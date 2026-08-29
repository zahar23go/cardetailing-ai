"""Личные KPI мастера (П2.3)."""

from datetime import datetime, timezone, timedelta

from app.models import Material
from app.modules.appointments.kpi_service import compute_shift_score
from app.schemas import TechCardBlockIn, TechCardCreate, TechCardItemIn
from app.services import tech_cards_service as tech_svc


async def _create_appointment(client, auth_headers, service_id, car_id, master_id=None):
    start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    body = {
        "service_id": service_id,
        "car_id": car_id,
        "start_time": start,
    }
    if master_id is not None:
        body["master_id"] = master_id
    resp = await client.post("/api/appointments", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


class TestMasterKpi:
    async def test_client_forbidden(self, client, auth_headers):
        resp = await client.get("/api/masters/me/kpi", headers=auth_headers)
        assert resp.status_code == 403

    async def test_empty_zeros(self, client, master_headers):
        resp = await client.get("/api/masters/me/kpi", headers=master_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["revenue"] == 0
        assert data["avg_check"] == 0
        assert data["completed_month"] == 0
        assert data["repeat_clients"] == 0
        assert data["score"] == 0
        assert len(data["sparkline_revenue"]) == 14
        assert data["score_hint"] == "техкарта · расход · повтор"

    async def test_score_formula(self):
        assert compute_shift_score(
            completed=0, compliance_pct=100, overspend_ratio=0, repeat_rate=0, no_show_rate=0,
        ) == 0.0
        # 100% техкарта, без перерасхода, без повторных, без no-show
        assert compute_shift_score(
            completed=1, compliance_pct=100, overspend_ratio=0, repeat_rate=0, no_show_rate=0,
        ) == 4.3

    async def test_revenue_after_close(
        self, client, admin_headers, auth_headers, master_headers, test_master, test_service, test_car,
    ):
        appt_id = await _create_appointment(
            client, auth_headers, test_service.id, test_car.id, master_id=test_master.id,
        )
        done = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed", "master_id": test_master.id},
            headers=admin_headers,
        )
        assert done.status_code == 200, done.text

        resp = await client.get("/api/masters/me/kpi", headers=master_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["completed_month"] == 1
        assert data["revenue"] == 5000.0
        assert data["avg_check"] == 5000.0
        assert data["unique_clients"] == 1
        assert data["repeat_clients"] == 0
        assert data["tech_compliance_pct"] == 100.0
        assert data["overspend_qty"] == 0
        assert data["score"] == 4.3
        assert sum(p["value"] for p in data["sparkline_revenue"]) == 5000.0

        listed = await client.get("/api/masters/me/appointments", headers=master_headers)
        assert listed.status_code == 200
        ids = [a["id"] for a in listed.json()["items"]]
        assert appt_id not in ids

    async def test_repeat_compliance_overspend(
        self,
        client,
        admin_headers,
        auth_headers,
        master_headers,
        test_master,
        test_service,
        test_car,
        db_session,
        default_tenant,
    ):
        mat = Material(
            name="Полироль KPI",
            category="chemistry",
            unit="ml",
            quantity=2000,
            min_quantity=50,
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
                name="ТК KPI",
                blocks=[
                    TechCardBlockIn(
                        title="Мойка",
                        items=[TechCardItemIn(material_id=mat.id, quantity=50)],
                    ),
                    TechCardBlockIn(
                        title="Полировка",
                        items=[TechCardItemIn(material_id=mat.id, quantity=50)],
                    ),
                ],
            ),
        )
        await db_session.commit()
        wash_id = card.blocks[0].id
        polish_id = card.blocks[1].id

        first = await _create_appointment(
            client, auth_headers, test_service.id, test_car.id, master_id=test_master.id,
        )
        closed1 = await client.post(
            f"/api/appointments/{first}/close",
            json={
                "steps": [
                    {"block_id": wash_id, "done": True},
                    {"block_id": polish_id, "done": True},
                ],
            },
            headers=admin_headers,
        )
        assert closed1.status_code == 200, closed1.text

        second = await _create_appointment(
            client, auth_headers, test_service.id, test_car.id, master_id=test_master.id,
        )
        closed2 = await client.post(
            f"/api/appointments/{second}/close",
            json={
                "steps": [
                    {"block_id": wash_id, "done": True},
                    {"block_id": polish_id, "done": False},
                ],
                "materials": [{"material_id": mat.id, "actual_qty": 80}],
            },
            headers=admin_headers,
        )
        assert closed2.status_code == 200, closed2.text
        assert closed2.json()["materials"][0]["norm_qty"] == 50.0

        resp = await client.get("/api/masters/me/kpi", headers=master_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["completed_month"] == 2
        assert data["revenue"] == 10000.0
        assert data["unique_clients"] == 1
        assert data["repeat_clients"] == 1
        assert data["repeat_rate"] == 100.0
        assert data["tech_steps_total"] == 4
        assert data["tech_steps_done"] == 3
        assert data["tech_compliance_pct"] == 75.0
        assert data["overspend_qty"] == 30.0
        assert data["overspend_cost"] == 60.0
        assert data["score"] == compute_shift_score(
            completed=2,
            compliance_pct=75.0,
            overspend_ratio=30.0 / 150.0,
            repeat_rate=1.0,
            no_show_rate=0.0,
        )
