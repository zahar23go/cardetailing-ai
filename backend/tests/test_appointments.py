"""
Тесты записей (appointments).

Проверяют создание, отмену и получение списка записей.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


class TestAppointments:
    """Набор тестов для эндпоинтов записей."""

    # ------------------------------------------------------------------
    # 1. Создание записи
    # ------------------------------------------------------------------
    async def test_create_appointment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Создание новой записи на услугу."""
        start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        payload = {
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": start_time,
            "notes": "Тестовая запись",
        }
        response = await client.post("/api/appointments", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["service_id"] == test_service.id
        assert data["car_id"] == test_car.id
        assert data["status"] == "pending"
        assert data["total_price"] == test_service.price  # без скидки
        assert "id" in data

    # ------------------------------------------------------------------
    # 2. Отмена записи клиентом
    # ------------------------------------------------------------------
    async def test_cancel_appointment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Отмена собственной записи в статусе pending."""
        # Сначала создаём запись
        start_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        create_payload = {
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": start_time,
        }
        create_resp = await client.post("/api/appointments", json=create_payload, headers=auth_headers)
        assert create_resp.status_code == 200
        appointment_id = create_resp.json()["id"]

        # Отменяем запись
        response = await client.put(
            f"/api/appointments/{appointment_id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "cancelled"

    # ------------------------------------------------------------------
    # 3. Получение списка своих записей
    # ------------------------------------------------------------------
    async def test_get_my_appointments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Получение списка записей текущего пользователя."""
        # Создаём пару записей
        for i in range(2):
            start_time = (datetime.now(timezone.utc) + timedelta(days=3 + i)).isoformat()
            payload = {
                "service_id": test_service.id,
                "car_id": test_car.id,
                "start_time": start_time,
            }
            resp = await client.post("/api/appointments", json=payload, headers=auth_headers)
            assert resp.status_code == 200

        # Получаем список
        response = await client.get("/api/appointments/me", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert isinstance(data, dict), "Ответ должен быть словарём с пагинацией"
        assert "items" in data, "Ответ должен содержать items"
        assert "total" in data, "Ответ должен содержать total"
        assert data["total"] == 2, f"Ожидалось 2 записи всего, получено {data['total']}"
        assert len(data["items"]) == 2, f"Ожидалось 2 записи, получено {len(data['items'])}"
