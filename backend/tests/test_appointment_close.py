"""Закрытие заезда: чек, склад, P&L snapshot, маржа по боксу."""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.models import Box, Expense, Material, MaterialMovement
from app.schemas import TechCardBlockIn, TechCardCreate, TechCardItemIn
from app.services import tech_cards_service as tech_svc


async def _create_appointment(client, auth_headers, service_id, car_id, box_id=None, master_id=None):
    start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    body = {
        "service_id": service_id,
        "car_id": car_id,
        "start_time": start,
    }
    if box_id is not None:
        body["box_id"] = box_id
    if master_id is not None:
        body["master_id"] = master_id
    resp = await client.post("/api/appointments", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


class TestAppointmentClose:
    async def test_put_complete_without_tech_card_still_works(
        self, client, admin_headers, auth_headers, test_service, test_car,
    ):
        appt_id = await _create_appointment(client, auth_headers, test_service.id, test_car.id)
        resp = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        preview = await client.get(
            f"/api/appointments/{appt_id}/close-preview",
            headers=admin_headers,
        )
        assert preview.status_code == 200
        data = preview.json()
        assert data["already_closed"] is True
        assert data["material_cost"] == 500.0

    async def test_close_writes_off_stock_and_snapshots_cost(
        self, client, admin_headers, auth_headers, db_session, default_tenant, test_service, test_car,
    ):
        mat = Material(
            name="Полироль",
            category="chemistry",
            unit="ml",
            quantity=1000,
            min_quantity=100,
            purchase_price=2.5,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        await tech_svc.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=test_service.id,
                name="ТК полировка",
                blocks=[
                    TechCardBlockIn(
                        title="Нанесение",
                        items=[TechCardItemIn(material_id=mat.id, quantity=50)],
                    )
                ],
            ),
        )
        await db_session.commit()

        appt_id = await _create_appointment(client, auth_headers, test_service.id, test_car.id)
        resp = await client.post(
            f"/api/appointments/{appt_id}/close",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        invoice = resp.json()
        assert invoice["material_cost"] == 125.0
        assert invoice["catalog_material_cost"] == 500.0
        assert invoice["price"] == 5000.0
        assert len(invoice["materials"]) == 1
        assert invoice["materials"][0]["applied_qty"] == 50.0
        assert invoice["materials"][0]["shortage"] == 0.0

        await db_session.refresh(mat)
        assert float(mat.quantity) == 950.0

        moves = (
            await db_session.execute(
                select(MaterialMovement).where(MaterialMovement.appointment_id == appt_id)
            )
        ).scalars().all()
        assert len(moves) == 1
        assert float(moves[0].delta) == -50.0

        again = await client.post(
            f"/api/appointments/{appt_id}/close",
            json={},
            headers=admin_headers,
        )
        assert again.status_code == 200
        await db_session.refresh(mat)
        assert float(mat.quantity) == 950.0

        test_service.material_cost = 999
        await db_session.commit()

        pl = await client.get("/api/analytics/pl", headers=admin_headers)
        assert pl.status_code == 200
        body = pl.json()
        assert body["total_material_cost"] == 125.0
        assert body["total_revenue"] == 5000.0

    async def test_close_does_not_fail_on_shortage(
        self, client, admin_headers, auth_headers, db_session, default_tenant, test_service, test_car,
    ):
        mat = Material(
            name="Шампунь",
            category="chemistry",
            unit="ml",
            quantity=10,
            min_quantity=5,
            purchase_price=1.0,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        await tech_svc.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=test_service.id,
                blocks=[
                    TechCardBlockIn(
                        title="Мойка",
                        items=[TechCardItemIn(material_id=mat.id, quantity=50)],
                    )
                ],
            ),
        )
        await db_session.commit()

        appt_id = await _create_appointment(client, auth_headers, test_service.id, test_car.id)
        resp = await client.post(f"/api/appointments/{appt_id}/close", json={}, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        row = resp.json()["materials"][0]
        assert row["applied_qty"] == 10.0
        assert row["shortage"] == 40.0
        assert row["line_cost"] == 10.0
        await db_session.refresh(mat)
        assert float(mat.quantity) == 0.0

    async def test_unchecked_step_skips_materials(
        self, client, admin_headers, auth_headers, db_session, default_tenant, test_service, test_car,
    ):
        mat = Material(
            name="Химия",
            category="chemistry",
            unit="ml",
            quantity=500,
            purchase_price=2.0,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        card = await tech_svc.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=test_service.id,
                blocks=[
                    TechCardBlockIn(
                        title="Мойка",
                        items=[TechCardItemIn(material_id=mat.id, quantity=30)],
                    ),
                    TechCardBlockIn(
                        title="Полировка",
                        items=[TechCardItemIn(material_id=mat.id, quantity=20)],
                    ),
                ],
            ),
        )
        await db_session.commit()
        wash_id = card.blocks[0].id
        polish_id = card.blocks[1].id

        appt_id = await _create_appointment(client, auth_headers, test_service.id, test_car.id)
        resp = await client.post(
            f"/api/appointments/{appt_id}/close",
            json={
                "steps": [
                    {"block_id": wash_id, "done": True},
                    {"block_id": polish_id, "done": False},
                ]
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        row = resp.json()["materials"][0]
        assert row["norm_qty"] == 30.0
        assert row["applied_qty"] == 30.0
        await db_session.refresh(mat)
        assert float(mat.quantity) == 470.0

    async def test_master_close(
        self, client, admin_headers, auth_headers, master_headers, test_master, test_service, test_car,
    ):
        appt_id = await _create_appointment(
            client, auth_headers, test_service.id, test_car.id, master_id=test_master.id,
        )
        started = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "in_progress", "master_id": test_master.id},
            headers=admin_headers,
        )
        assert started.status_code == 200

        preview = await client.get(
            f"/api/masters/me/appointments/{appt_id}/close-preview",
            headers=master_headers,
        )
        assert preview.status_code == 200

        closed = await client.post(
            f"/api/masters/me/appointments/{appt_id}/close",
            json={},
            headers=master_headers,
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["material_cost"] == 500.0

        listed = await client.get("/api/masters/me/appointments", headers=master_headers)
        ids = [a["id"] for a in listed.json()["items"]]
        assert appt_id not in ids

    async def test_pl_box_margins(
        self, client, admin_headers, auth_headers, db_session, default_tenant, test_service, test_car,
    ):
        box1 = Box(name="Бокс 1", tenant_id=default_tenant.id, sort_order=0, is_active=True)
        box2 = Box(name="Бокс 2", tenant_id=default_tenant.id, sort_order=1, is_active=True)
        db_session.add_all([box1, box2])
        await db_session.commit()
        await db_session.refresh(box1)
        await db_session.refresh(box2)

        db_session.add(Expense(
            tenant_id=default_tenant.id,
            name="Аренда",
            amount=1000,
            category="rent",
            expense_date=datetime.now(timezone.utc),
        ))
        await db_session.commit()

        a1 = await _create_appointment(client, auth_headers, test_service.id, test_car.id, box_id=box1.id)
        a2 = await _create_appointment(client, auth_headers, test_service.id, test_car.id, box_id=box2.id)
        assert (await client.put(f"/api/appointments/{a1}", json={"status": "completed"}, headers=admin_headers)).status_code == 200
        assert (await client.put(f"/api/appointments/{a2}", json={"status": "completed"}, headers=admin_headers)).status_code == 200

        pl = await client.get("/api/analytics/pl", headers=admin_headers)
        assert pl.status_code == 200
        boxes = {row["box_name"]: row for row in pl.json()["box_margins"]}
        assert "Бокс 1" in boxes
        assert "Бокс 2" in boxes
        assert boxes["Бокс 1"]["total_revenue"] == 5000.0
        assert boxes["Бокс 1"]["total_material_cost"] == 500.0
        assert boxes["Бокс 1"]["allocated_expenses"] == 500.0
        assert boxes["Бокс 1"]["net_profit"] == 4000.0
        assert boxes["Бокс 2"]["allocated_expenses"] == 500.0
