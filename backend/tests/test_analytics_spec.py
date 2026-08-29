"""Аналитика П1.1: когорты, treemap, sparkline, загрузка."""

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


class TestAnalyticsSpec:
    async def test_kpi_has_sparkline(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/analytics/kpi", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_clients" in data
        assert len(data["sparkline_revenue"]) == 14
        assert len(data["sparkline_appointments"]) == 14
        assert "date" in data["sparkline_revenue"][0]

    async def test_spec_shape(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/analytics/spec", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "cohorts" in data
        assert "treemap" in data
        assert "masters" in data
        assert "boxes" in data
        assert data["period_days"] == 7
        assert len(data["cohorts"]) == 6

    async def test_spec_with_completed(
        self,
        client: AsyncClient,
        admin_headers: dict,
        auth_headers: dict,
        test_service,
        test_car,
    ):
        start = datetime.now(timezone.utc) - timedelta(hours=2)
        created = await client.post(
            "/api/appointments",
            json={
                "service_id": test_service.id,
                "car_id": test_car.id,
                "start_time": start.isoformat(),
            },
            headers=auth_headers,
        )
        assert created.status_code == 200, created.text
        appt_id = created.json()["id"]
        done = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed"},
            headers=admin_headers,
        )
        assert done.status_code == 200, done.text

        spec = await client.get("/api/analytics/spec", headers=admin_headers)
        assert spec.status_code == 200
        tree = spec.json()["treemap"]
        assert any(n["count"] >= 1 for n in tree)

        kpi = await client.get("/api/analytics/kpi", headers=admin_headers)
        assert sum(p["value"] for p in kpi.json()["sparkline_completed"]) >= 1
