"""Тесты аналитики по услугам."""

from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


class TestServiceAnalytics:
    """Тесты для аналитики услуг."""

    async def test_analytics_endpoint(self, client, admin_headers, test_service, test_car, auth_headers):
        """✅ Эндпоинт аналитики возвращает данные."""
        # Создаём завершённую запись для данных
        start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        appt_id = resp.json()["id"]

        # Подтверждаем и завершаем
        await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed"},
            headers=admin_headers,
        )

        # Получаем аналитику
        response = await client.get(
            "/api/analytics/services?months=6",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        assert "top_services" in data
        assert "forecast" in data
