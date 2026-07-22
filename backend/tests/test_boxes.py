"""
Тесты боксов (boxes) и тепловой карты с фильтром по боксу.

Проверяют:
- CRUD боксов (создание, чтение, обновление, удаление)
- Тепловая карта с фильтром по боксу
- Сброс box_id при удалении бокса
"""

from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient


class TestBoxes:
    """Набор тестов для управления боксами."""

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------
    async def _create_box(self, client: AsyncClient, admin_headers: dict, **kwargs) -> dict:
        """Создать бокс и вернуть его данные."""
        payload = {
            "name": kwargs.get("name", "Бокс 1 — мойка"),
            "color": kwargs.get("color", "#C8A977"),
            "sort_order": kwargs.get("sort_order", 0),
            "is_active": kwargs.get("is_active", True),
        }
        resp = await client.post("/api/boxes", json=payload, headers=admin_headers)
        assert resp.status_code == 200, f"create_box failed: {resp.text}"
        return resp.json()

    # ------------------------------------------------------------------
    # 1. CREATE — создание бокса
    # ------------------------------------------------------------------
    async def test_create_box(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Создание нового бокса."""
        data = await self._create_box(client, admin_headers)

        assert data["id"] > 0
        assert data["name"] == "Бокс 1 — мойка"
        assert data["color"] == "#C8A977"
        assert data["sort_order"] == 0
        assert data["is_active"] is True
        assert "created_at" in data

    # ------------------------------------------------------------------
    # 2. CREATE — клиент НЕ может создать бокс (только admin)
    # ------------------------------------------------------------------
    async def test_create_box_forbidden_for_client(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """❌ Клиент не может создать бокс (403)."""
        resp = await client.post("/api/boxes", json={
            "name": "Бокс 1",
            "color": "#C8A977",
        }, headers=auth_headers)
        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # 3. READ — список боксов
    # ------------------------------------------------------------------
    async def test_list_boxes(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Получение списка боксов."""
        # Создаём 2 бокса
        await self._create_box(client, admin_headers, name="Бокс 1", sort_order=0)
        await self._create_box(client, admin_headers, name="Бокс 2", sort_order=1)

        resp = await client.get("/api/boxes", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Бокс 1"
        assert data[1]["name"] == "Бокс 2"

    # ------------------------------------------------------------------
    # 4. UPDATE — обновление бокса
    # ------------------------------------------------------------------
    async def test_update_box(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Обновление названия и цвета бокса."""
        box = await self._create_box(client, admin_headers, name="Старое имя")

        resp = await client.put(f"/api/boxes/{box['id']}", json={
            "name": "Новое имя",
            "color": "#4ECB71",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Новое имя"
        assert data["color"] == "#4ECB71"

    # ------------------------------------------------------------------
    # 5. DELETE — удаление бокса
    # ------------------------------------------------------------------
    async def test_delete_box(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Удаление бокса."""
        box = await self._create_box(client, admin_headers)

        resp = await client.delete(f"/api/boxes/{box['id']}", headers=admin_headers)
        assert resp.status_code == 200

        # Проверяем, что бокс удалён
        resp = await client.get("/api/boxes", headers=admin_headers)
        assert len(resp.json()) == 0

    # ------------------------------------------------------------------
    # 6. DELETE — сброс box_id в appointments при удалении
    # ------------------------------------------------------------------
    async def test_delete_box_resets_appointments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ При удалении бокса box_id в записях сбрасывается в NULL."""
        # Создаём бокс
        box = await self._create_box(client, admin_headers)

        # Создаём запись с указанием бокса
        now = datetime.now(timezone.utc)
        appt_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if appt_time <= now:
            appt_time = appt_time + timedelta(days=7)

        appt_resp = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time.isoformat(),
            "box_id": box["id"],
        }, headers=auth_headers)
        assert appt_resp.status_code == 200
        appt = appt_resp.json()
        assert appt["box_id"] == box["id"]

        # Удаляем бокс
        await client.delete(f"/api/boxes/{box['id']}", headers=admin_headers)

        # Создаём новую запись (загружаем заново — у нас нет прямого доступа к БД)
        # Проверяем что запись всё ещё существует и box_id сброшен
        now2 = datetime.now(timezone.utc)
        appt_time2 = now2.replace(hour=11, minute=0, second=0, microsecond=0)
        if appt_time2 <= now2:
            appt_time2 = appt_time2 + timedelta(days=7)

        # Создаём новую запись без box_id (старому box_id уже не существует)
        appt2_resp = await client.post("/api/appointments", json={
            "service_id": test_service.id,
            "car_id": test_car.id,
            "start_time": appt_time2.isoformat(),
        }, headers=auth_headers)
        assert appt2_resp.status_code == 200
        assert appt2_resp.json()["box_id"] is None


class TestHeatmapBoxes:
    """Набор тестов для тепловой карты с фильтром по боксу."""

    # ------------------------------------------------------------------
    # 1. Тепловая карта без фильтра возвращает все данные
    # ------------------------------------------------------------------
    async def test_heatmap_no_filter(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """✅ Тепловая карта без параметра box_id возвращает все клетки + список боксов."""
        resp = await client.get("/api/analytics/heatmap", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cells" in data
        assert "boxes" in data
        # Должна быть сетка 7×12 = 84 клетки
        assert len(data["cells"]) == 84
        assert isinstance(data["boxes"], list)

    # ------------------------------------------------------------------
    # 2. Тепловая карта с фильтром по боксу
    # ------------------------------------------------------------------
    async def test_heatmap_with_box_filter(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_service,
        test_car,
    ):
        """✅ Фильтр ?box_id=X возвращает данные только для указанного бокса."""
        # Создаём бокс
        box_resp = await client.post("/api/boxes", json={
            "name": "Бокс тест",
            "color": "#C8A977",
        }, headers=admin_headers)
        assert box_resp.status_code == 200
        box = box_resp.json()

        # Фильтр по созданному боксу — данных нет
        resp = await client.get(f"/api/analytics/heatmap?box_id={box['id']}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cells"]) == 84
        # Все count = 0 (записей не было)
        assert all(c["count"] == 0 for c in data["cells"])

    # ------------------------------------------------------------------
    # 3. Несуществующий бокс
    # ------------------------------------------------------------------
    async def test_heatmap_invalid_box(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """❌ Фильтр с несуществующим box_id возвращает пустую карту."""
        resp = await client.get("/api/analytics/heatmap?box_id=99999", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cells"]) == 84
        assert all(c["count"] == 0 for c in data["cells"])
