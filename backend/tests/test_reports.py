"""Тесты отчётов и экспорта."""

from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


class TestReports:
    """Тесты для отчётов."""

    async def test_revenue_report(self, client, admin_headers, auth_headers, test_service, test_car):
        """✅ Отчёт по выручке возвращает данные."""
        # Создаём завершённую запись
        start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        appt_id = resp.json()["id"]

        await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed"},
            headers=admin_headers,
        )

        response = await client.get("/api/reports/revenue?period=month", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "by_service" in data
        assert "by_master" in data
        assert "details" in data

    async def test_csv_export(self, client, admin_headers):
        """✅ CSV экспорт возвращает файл."""
        response = await client.get("/api/reports/revenue/csv?period=month", headers=admin_headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
