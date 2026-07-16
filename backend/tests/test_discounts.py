"""
Тесты скидок (discounts).

Проверяют логику автоприменения скидок Happy Hours:
- Скидка применяется в будни с 10:00 до 14:00
- Скидка НЕ применяется вне часов (например, в 16:00)
- Скидка НЕ применяется в выходные
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


class TestDiscounts:
    """Набор тестов для правил скидок."""

    # ------------------------------------------------------------------
    # Вспомогательный метод: создать правило Happy Hours
    # ------------------------------------------------------------------
    async def _create_happy_hours_rule(self, client: AsyncClient, admin_headers: dict) -> dict:
        """Создать правило скидки Happy Hours (10% скидка с 10 до 14 в будни)."""
        payload = {
            "name": "Happy Hours 10-14",
            "type": "happy_hours",
            "conditions": {
                "hour_start": 10,
                "hour_end": 14,
                "utc_offset": 0,
                "min_discount": 0,
            },
            "discount_percent": 10,
            "is_active": True,
        }
        response = await client.post("/api/discounts", json=payload, headers=admin_headers)
        return response

    # ------------------------------------------------------------------
    # 1. Скидка применяется в Happy Hours (будни, 10-14)
    # ------------------------------------------------------------------
    async def test_happy_hours_discount_applied(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """
        ✅ Скидка Happy Hours применяется при записи
        на будний день в интервале 10:00-14:00.
        """
        # Создаём правило скидки
        rule_resp = await self._create_happy_hours_rule(client, admin_headers)
        assert rule_resp.status_code == 200, f"Failed to create rule: {rule_resp.text}"

        # Выбираем ближайший будний день (Monday=0 ... Friday=4)
        now = datetime.now(timezone.utc)
        days_ahead = 0
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() < 5:  # будний день
                days_ahead = i
                break

        # Ставим время на 11:00 (внутри happy hours 10-14)
        happy_hour_start = (now + timedelta(days=days_ahead)).replace(
            hour=11, minute=0, second=0, microsecond=0
        )

        payload = {
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": happy_hour_start.isoformat(),
        }
        response = await client.post("/api/appointments", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Скидка 10% должна быть применена
        price = float(test_service.price)
        expected_price = round(price * 0.9, 2)
        assert data["total_price"] == expected_price, (
            f"Ожидалась цена со скидкой {expected_price}, "
            f"получено {data['total_price']}"
        )
        expected_discount = round(price * 0.1, 2)
        assert data["discount_applied"] == expected_discount, (
            f"Ожидалась скидка {expected_discount}, "
            f"получено {data['discount_applied']}"
        )

    # ------------------------------------------------------------------
    # 2. Скидка НЕ применяется вне Happy Hours (16:00)
    # ------------------------------------------------------------------
    async def test_happy_hours_outside_hours(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """
        ❌ Скидка НЕ применяется, если запись вне часов Happy Hours
        (например, в 16:00).
        """
        # Создаём правило скидки
        rule_resp = await self._create_happy_hours_rule(client, admin_headers)
        assert rule_resp.status_code == 200

        # Выбираем ближайший будний день
        now = datetime.now(timezone.utc)
        days_ahead = 0
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() < 5:
                days_ahead = i
                break

        # Ставим время на 16:00 (вне happy hours 10-14)
        outside_hour = (now + timedelta(days=days_ahead)).replace(
            hour=16, minute=0, second=0, microsecond=0
        )

        payload = {
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": outside_hour.isoformat(),
        }
        response = await client.post("/api/appointments", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Скидка не должна быть применена
        assert data["total_price"] == test_service.price, (
            f"Цена без скидки: ожидалось {test_service.price}, "
            f"получено {data['total_price']}"
        )
        assert data["discount_applied"] == 0, (
            f"Скидка не должна применяться, получено {data['discount_applied']}"
        )

    # ------------------------------------------------------------------
    # 3. Скидка НЕ применяется в выходные
    # ------------------------------------------------------------------
    async def test_happy_hours_weekend(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """
        ❌ Скидка НЕ применяется, если запись на выходной день
        (Saturday=5 или Sunday=6), даже в Happy Hours.
        """
        # Создаём правило скидки
        rule_resp = await self._create_happy_hours_rule(client, admin_headers)
        assert rule_resp.status_code == 200

        # Выбираем ближайшую субботу или воскресенье
        now = datetime.now(timezone.utc)
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() >= 5:  # выходной (5=Sat, 6=Sun)
                # Ставим время на 11:00 (попадает в happy hours по времени,
                # но не по дню недели)
                weekend_start = candidate.replace(
                    hour=11, minute=0, second=0, microsecond=0
                )

                payload = {
                    "service_id": test_service.id,
                    "car_id": test_car.id,
                    "start_time": weekend_start.isoformat(),
                }
                response = await client.post("/api/appointments", json=payload, headers=auth_headers)
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                data = response.json()

                # Скидка не должна быть применена
                assert data["total_price"] == test_service.price, (
                    f"В выходной скидка не применяется: "
                    f"ожидалось {test_service.price}, получено {data['total_price']}"
                )
                assert data["discount_applied"] == 0, (
                    f"В выходной скидка не применяется, "
                    f"получено {data['discount_applied']}"
                )
                return  # выполнили тест для выходного

        pytest.skip("Не удалось найти выходной день в ближайшую неделю")
