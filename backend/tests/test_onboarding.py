"""Онбординг владельца: статус, мастера, KPI загрузки."""

from httpx import AsyncClient


class TestOwnerOnboarding:
    async def test_needs_wizard_when_salon_empty(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.get("/api/onboarding", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["needs_wizard"] is True
        assert data["completed"] is False
        assert data["boxes"] == 0

    async def test_complete_and_create_master(
        self, client: AsyncClient, admin_headers: dict
    ):
        created = await client.post(
            "/api/users",
            json={
                "full_name": "Сергей",
                "phone": "79001111999",
                "password": "password123",
                "role": "master",
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        assert created.json()["role"] == "master"

        done = await client.post("/api/onboarding/complete", headers=admin_headers)
        assert done.status_code == 200, done.text
        assert done.json()["completed"] is True
        assert done.json()["needs_wizard"] is False

    async def test_kpi_occupancy_fields(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.get("/api/analytics/kpi", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "occupancy_pct" in data
        assert "week_revenue" in data
        assert "week_change_percent" in data
