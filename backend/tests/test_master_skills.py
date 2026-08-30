"""Навыки мастера: услуги/техкарты и комиссия в чеке."""

from datetime import datetime, timezone, timedelta

from httpx import AsyncClient

from app.models import Service


class TestMasterSkills:
    async def test_empty_skills_lists_all_masters(
        self, client: AsyncClient, auth_headers: dict, test_master,
    ):
        resp = await client.get("/api/masters", headers=auth_headers)
        assert resp.status_code == 200
        names = [m["full_name"] for m in resp.json()["items"]]
        assert test_master.full_name in names

    async def test_put_and_filter_by_service(
        self,
        client: AsyncClient,
        admin_headers: dict,
        auth_headers: dict,
        db_session,
        default_tenant,
        test_master,
        test_service,
    ):
        other = Service(
            name="Мойка кузова",
            description="Двухфазная",
            category="Мойка",
            price=2000,
            duration=40,
            material_cost=100,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        put = await client.put(
            f"/api/masters/{test_master.id}/skills",
            json={
                "commission_percent": 15,
                "items": [{"service_id": test_service.id, "commission_percent": 15}],
            },
            headers=admin_headers,
        )
        assert put.status_code == 200, put.text
        body = put.json()
        assert body["commission_percent"] == 15
        assert [i["service_id"] for i in body["items"]] == [test_service.id]

        got = await client.get(f"/api/masters/{test_master.id}/skills", headers=admin_headers)
        assert got.status_code == 200
        assert got.json()["items"][0]["service_id"] == test_service.id

        match = await client.get(
            f"/api/masters?service_id={test_service.id}",
            headers=auth_headers,
        )
        assert test_master.id in [m["id"] for m in match.json()["items"]]

        miss = await client.get(
            f"/api/masters?service_id={other.id}",
            headers=auth_headers,
        )
        assert test_master.id not in [m["id"] for m in miss.json()["items"]]

    async def test_booking_rejects_master_without_skill(
        self,
        client: AsyncClient,
        admin_headers: dict,
        auth_headers: dict,
        test_master,
        test_service,
        test_car,
        db_session,
        default_tenant,
    ):
        other = Service(
            name="Химчистка",
            description="Салон",
            category="Салон",
            price=3000,
            duration=90,
            material_cost=200,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        assert (await client.put(
            f"/api/masters/{test_master.id}/skills",
            json={"commission_percent": 10, "items": [{"service_id": other.id}]},
            headers=admin_headers,
        )).status_code == 200

        start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=16, minute=0, second=0, microsecond=0,
        )
        denied = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "master_id": test_master.id,
            "start_time": start.isoformat(),
        }, headers=auth_headers)
        assert denied.status_code == 400

        ok = await client.post("/api/appointments", json={
            "service_id": other.id,
            "car_id": test_car.id,
            "master_id": test_master.id,
            "start_time": (start + timedelta(hours=2)).isoformat(),
        }, headers=auth_headers)
        assert ok.status_code == 200, ok.text

    async def test_close_snapshots_commission(
        self,
        client: AsyncClient,
        admin_headers: dict,
        auth_headers: dict,
        test_master,
        test_service,
        test_car,
    ):
        assert (await client.put(
            f"/api/masters/{test_master.id}/skills",
            json={
                "commission_percent": 20,
                "items": [{"service_id": test_service.id, "commission_percent": 20}],
            },
            headers=admin_headers,
        )).status_code == 200

        start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        created = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "master_id": test_master.id,
            "start_time": start,
        }, headers=auth_headers)
        assert created.status_code == 200, created.text
        appt_id = created.json()["id"]

        closed = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed", "master_id": test_master.id},
            headers=admin_headers,
        )
        assert closed.status_code == 200

        preview = await client.get(
            f"/api/appointments/{appt_id}/close-preview",
            headers=admin_headers,
        )
        assert preview.status_code == 200
        data = preview.json()
        price = float(test_service.price)
        assert data["commission_percent"] == 20
        assert data["commission_amount"] == round(price * 0.2, 2)
        assert data["gross_profit"] == round(price - 500.0, 2)

    async def test_client_cannot_edit_skills(
        self, client: AsyncClient, auth_headers: dict, test_master, test_service,
    ):
        resp = await client.put(
            f"/api/masters/{test_master.id}/skills",
            json={"commission_percent": 50, "items": [{"service_id": test_service.id}]},
            headers=auth_headers,
        )
        assert resp.status_code in (401, 403)
