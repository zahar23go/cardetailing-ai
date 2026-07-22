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
            "conditions": {},
            "discount_percent": 10,
            "slot_start": "10:00",
            "slot_end": "14:00",
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

    # ------------------------------------------------------------------
    # 4. Аналитика скидок /api/discounts/analytics
    # ------------------------------------------------------------------
    async def test_discount_analytics_no_data(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Аналитика скидок без правил возвращает пустой результат."""
        resp = await client.get("/api/discounts/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "rules" in data
        assert "summary" in data
        assert data["summary"]["total_rules"] == 0
        assert data["summary"]["active_rules"] == 0
        assert data["summary"]["total_discount_uses"] == 0

    async def test_discount_analytics_with_rules(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Аналитика скидок с правилами возвращает корректную статистику."""
        # Создаём правило
        rule_resp = await self._create_happy_hours_rule(client, admin_headers)
        assert rule_resp.status_code == 200

        resp = await client.get("/api/discounts/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        # В summary не меньше 1 правила, 1 активное, 0 использований
        assert data["summary"]["total_rules"] >= 1
        assert data["summary"]["active_rules"] >= 1
        assert data["summary"]["total_discount_uses"] == 0
        assert len(data["rules"]) >= 1

        # Проверяем структуру объекта правила
        rule = data["rules"][0]
        assert "rule_id" in rule
        assert "rule_name" in rule
        assert "rule_type" in rule
        assert rule["rule_type"] == "happy_hours"
        assert "usage_count" in rule
        assert "total_discount_amount" in rule
        assert "roi_percent" in rule

    async def test_discount_analytics_with_usage(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Аналитика скидок показывает использование скидки."""
        # 1. Создаём правило Happy Hours
        rule_resp = await self._create_happy_hours_rule(client, admin_headers)
        assert rule_resp.status_code == 200

        # 2. Создаём запись в будний день в 11:00 (попадает в Happy Hours)
        now = datetime.now(timezone.utc)
        days_ahead = 0
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() < 5:
                days_ahead = i
                break

        appt_time = (now + timedelta(days=days_ahead)).replace(
            hour=11, minute=0, second=0, microsecond=0
        )
        appt_resp = await client.post(
            "/api/appointments",
            json={
                "service_id": test_service.id,
                "car_id": test_car.id,
                "start_time": appt_time.isoformat(),
            },
            headers=auth_headers,
        )
        assert appt_resp.status_code == 200
        appt_data = appt_resp.json()
        # Скидка применена?
        assert appt_data["discount_applied"] > 0

        # 3. Запрашиваем аналитику — должно быть 1 использование
        resp = await client.get("/api/discounts/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["summary"]["total_rules"] >= 1
        assert data["summary"]["total_discount_uses"] >= 1
        assert data["summary"]["total_discount_amount"] > 0

        # Проверяем детали по правилу
        rule = data["rules"][0]
        assert rule["usage_count"] >= 1
        assert rule["total_discount_amount"] > 0


class TestServiceDiscount:
    """Тесты скидки на конкретную услугу (тип service)."""

    # ------------------------------------------------------------------
    # 1. Скидка service применяется к нужной услуге
    # ------------------------------------------------------------------
    async def test_service_discount_applied(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Скидка 'На услугу' применяется, если service_id совпадает."""
        # Создаём правило скидки на конкретную услугу
        resp = await client.post("/api/discounts", json={
            "name": "Скидка на полировку",
            "type": "service",
            "discount_percent": 15,
            "service_id": test_service.id,
            "is_active": True,
        }, headers=admin_headers)
        assert resp.status_code == 200

        now = datetime.now(timezone.utc)
        appt_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if appt_time <= now:
            appt_time = appt_time + timedelta(days=7)

        appt_resp = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
        }, headers=auth_headers)
        assert appt_resp.status_code == 200
        data = appt_resp.json()

        price = float(test_service.price)
        expected_price = round(price * 0.85, 2)
        assert data["total_price"] == expected_price, (
            f"Ожидалась цена со скидкой {expected_price}, получено {data['total_price']}"
        )

    # ------------------------------------------------------------------
    # 2. Скидка service НЕ применяется к другой услуге
    # ------------------------------------------------------------------
    async def test_service_discount_not_applied_to_other_service(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
        db_session,
    ):
        """❌ Скидка на услугу A не применяется к услуге B."""
        # Создаём другую услугу
        from app.models import Service
        other_service = Service(
            name="Химчистка салона",
            description="Полная химчистка",
            category="Детейлинг",
            price=8000.00,
            duration=180,
            material_cost=1000.00,
            is_active=True,
            tenant_id=test_service.tenant_id,
        )
        db_session.add(other_service)
        await db_session.commit()
        await db_session.refresh(other_service)

        # Создаём правило на test_service
        await client.post("/api/discounts", json={
            "name": "Скидка на полировку",
            "type": "service",
            "discount_percent": 15,
            "service_id": test_service.id,
            "is_active": True,
        }, headers=admin_headers)

        # Запись на другую услугу — скидка не применяется
        now = datetime.now(timezone.utc)
        appt_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if appt_time <= now:
            appt_time = appt_time + timedelta(days=7)

        appt_resp = await client.post("/api/appointments", json={
            "service_id": other_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
        }, headers=auth_headers)
        assert appt_resp.status_code == 200
        data = appt_resp.json()
        assert data["total_price"] == float(other_service.price)
        assert data["discount_applied"] == 0


class TestClientDiscount:
    """Тесты персональной скидки для клиента (тип client)."""

    # ------------------------------------------------------------------
    # 1. Персональная скидка применяется
    # ------------------------------------------------------------------
    async def test_client_discount_applied(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
        test_user,
    ):
        """✅ Персональная скидка применяется для указанного клиента."""
        resp = await client.post("/api/discounts", json={
            "name": "Персональная 20%",
            "type": "client",
            "discount_percent": 20,
            "client_id": test_user.id,
            "is_active": True,
        }, headers=admin_headers)
        assert resp.status_code == 200

        now = datetime.now(timezone.utc)
        appt_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if appt_time <= now:
            appt_time = appt_time + timedelta(days=7)

        appt_resp = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
        }, headers=auth_headers)
        assert appt_resp.status_code == 200
        data = appt_resp.json()

        price = float(test_service.price)
        expected_price = round(price * 0.8, 2)
        assert data["total_price"] == expected_price, (
            f"Ожидалась персональная скидка, цена {expected_price}, получено {data['total_price']}"
        )


class TestMinPriceDiscount:
    """Тест защиты минимальной цены (min_price)."""

    async def test_min_price_protection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Скидка не уходит ниже min_price (указано в conditions)."""
        # Услуга стоит 5000, min_price = 4500, скидка 20% = 1000
        # Обычная цена со скидкой: 5000 - 1000 = 4000
        # Но min_price = 4500, значит реальная скидка = 500
        resp = await client.post("/api/discounts", json={
            "name": "Скидка с min_price",
            "type": "happy_hours",
            "discount_percent": 20,
            "slot_start": "09:00",
            "slot_end": "18:00",
            "conditions": {"min_price": 4500},
            "is_active": True,
        }, headers=admin_headers)
        assert resp.status_code == 200

        now = datetime.now(timezone.utc)
        # Ближайший будний день, 10 утра (попадает в 09-18)
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() < 5:
                appt_time = candidate.replace(hour=10, minute=0, second=0, microsecond=0)
                break
        else:
            appt_time = (now + timedelta(days=7)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )

        appt_resp = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
        }, headers=auth_headers)
        assert appt_resp.status_code == 200
        data = appt_resp.json()

        # Цена не ниже min_price = 4500
        assert data["total_price"] >= 4500, (
            f"Цена ({data['total_price']}) ниже min_price (4500)"
        )
        # Скидка должна быть 500 (5000 - 4500), а не 1000 (20% от 5000)
        assert data["discount_applied"] == 500, (
            f"Скидка должна быть урезана до 500, получено {data['discount_applied']}"
        )


class TestDiscountAnalyticsNew:
    """Тесты нового эндпоинта аналитики скидок (/api/analytics/discounts)."""

    async def test_analytics_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Пустая аналитика."""
        resp = await client.get("/api/analytics/discounts", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rules"] == 0
        assert data["active_rules"] == 0
        assert data["total_times_used"] == 0
        assert data["total_discount_amount"] == 0
        assert data["unique_clients_affected"] == 0
        assert data["top_rules"] == []

    async def test_analytics_with_rules(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Аналитика с правилами (без использований)."""
        await client.post("/api/discounts", json={
            "name": "Тестовое правило",
            "type": "happy_hours",
            "discount_percent": 10,
            "slot_start": "10:00",
            "slot_end": "14:00",
            "is_active": True,
        }, headers=admin_headers)

        resp = await client.get("/api/analytics/discounts", headers=admin_headers)
        data = resp.json()
        assert data["total_rules"] >= 1
        assert data["active_rules"] >= 1
        assert data["total_times_used"] == 0
        assert data["top_rules"] == []

    async def test_analytics_with_usage(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Аналитика показывает использования."""
        # Правило скидки 10%
        await client.post("/api/discounts", json={
            "name": "Happy 10%",
            "type": "happy_hours",
            "discount_percent": 10,
            "slot_start": "09:00",
            "slot_end": "18:00",
            "is_active": True,
        }, headers=admin_headers)

        # Создаём запись (будни, 10:00)
        now = datetime.now(timezone.utc)
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            if candidate.weekday() < 5:
                appt_time = candidate.replace(hour=10, minute=0, second=0, microsecond=0)
                break
        else:
            appt_time = (now + timedelta(days=7)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )

        await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
        }, headers=auth_headers)

        # Проверяем аналитику
        resp = await client.get("/api/analytics/discounts", headers=admin_headers)
        data = resp.json()
        assert data["total_times_used"] >= 1
        assert data["total_discount_amount"] > 0
        assert data["unique_clients_affected"] >= 1
        assert len(data["top_rules"]) >= 1

        top = data["top_rules"][0]
        assert top["times_used"] >= 1
        assert top["total_discount"] > 0
        assert top["client_count"] >= 1
        assert "rule_name" in top
        assert "rule_type" in top
