"""Тарифы салона: Базовый / Про / Бизнес."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from httpx import AsyncClient

from app.modules.plans import PLANS, modules_for_plan


class TestPlans:
    async def test_default_modules_include_appointments(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        resp = await client.get("/api/modules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "business"
        assert "appointments" in data["modules"]
        assert "ai" in data["modules"]
        assert data["features"]["financier"] is True

    async def test_catalog(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/plans", headers=auth_headers)
        assert resp.status_code == 200
        ids = {p["id"] for p in resp.json()}
        assert ids == {"basic", "pro", "business"}
        basic = next(p for p in resp.json() if p["id"] == "basic")
        assert basic["price"] == 2990
        assert basic["appointment_limit"] == 150

    async def test_basic_hides_ai(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        default_tenant,
    ):
        default_tenant.plan = "basic"
        await db_session.commit()
        resp = await client.get("/api/modules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "basic"
        assert "ai" not in data["modules"]
        assert "appointments" in data["modules"]
        assert data["features"]["financier"] is False

        consult = await client.post(
            "/api/ai/consultant",
            json={"question": "Что есть?"},
            headers=auth_headers,
        )
        assert consult.status_code == 403

    async def test_admin_cannot_set_plan(
        self,
        client: AsyncClient,
        admin_headers: dict,
        default_tenant,
    ):
        resp = await client.put(
            f"/api/tenants/{default_tenant.id}/plan",
            json={"plan": "basic"},
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_super_admin_sets_plan(
        self,
        client: AsyncClient,
        db_session,
        default_tenant,
        test_admin,
    ):
        test_admin.role = "super_admin"
        await db_session.commit()
        from app.core.auth import create_token
        token = create_token(test_admin.id, str(default_tenant.id))
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.put(
            f"/api/tenants/{default_tenant.id}/plan",
            json={"plan": "pro"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["plan"] == "pro"

    async def test_basic_appointment_quota(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        default_tenant,
        test_user,
        test_car,
        test_service,
    ):
        default_tenant.plan = "basic"
        await db_session.commit()
        with patch.dict(PLANS["basic"], {"appointment_limit": 1}):
            start = datetime.now(timezone.utc) + timedelta(days=3)
            first = await client.post(
                "/api/appointments",
                json={
                    "service_id": test_service.id,
                    "car_id": test_car.id,
                    "start_time": start.isoformat(),
                },
                headers=auth_headers,
            )
            assert first.status_code == 200, first.text
            second = await client.post(
                "/api/appointments",
                json={
                    "service_id": test_service.id,
                    "car_id": test_car.id,
                    "start_time": (start + timedelta(hours=3)).isoformat(),
                },
                headers=auth_headers,
            )
            assert second.status_code == 403
            assert "150" in second.json()["detail"] or "лимит" in second.json()["detail"].lower() or "Базовый" in second.json()["detail"]

    def test_pro_has_ai_without_financier(self):
        mods = modules_for_plan("pro")
        assert "ai" in mods
        assert "analytics" in mods
        assert PLANS["pro"]["features"]["financier"] is False
        assert PLANS["pro"]["features"]["branding"] is False
