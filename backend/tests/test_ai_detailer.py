"""Тесты AI-детейлера: осмотр, допродажи, слот по боксам, сводка мастеру.

Чат /api/ai/consultant не меняется — проверяется отдельно в test_ai.py.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models import Appointment, Box, BoxService, Service


class TestAIDetailer:
    async def test_consultant_still_works(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        fake = "Рекомендуем комплексную мойку."
        with patch(
            "app.modules.ai.router.get_consultant_response",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            resp = await client.post(
                "/api/ai/consultant",
                json={"question": "Что есть в каталоге?"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["response"] == fake

    async def test_inspect_unauthorized(self, client: AsyncClient):
        resp = await client.post("/api/ai/detailer/inspect", json={"tags": ["chips"]})
        assert resp.status_code in (401, 403)

    async def test_inspect_chips_matches_polish(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_service: Service,
        test_car,
        db_session,
        default_tenant,
    ):
        extra = Service(
            name="Химчистка салона",
            description="Салон и кожа",
            category="Салон",
            price=3500,
            duration=90,
            material_cost=200,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        db_session.add(extra)
        await db_session.commit()
        await db_session.refresh(extra)

        resp = await client.post(
            "/api/ai/detailer/inspect",
            json={
                "tags": ["chips", "interior"],
                "notes": "перед зимой",
                "car_id": test_car.id,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] > 0
        assert "chips" in data["tags"]
        assert "interior" in data["tags"]
        offered = {data["primary"]["service_id"], *[u["service_id"] for u in data["upsells"]]}
        assert test_service.id in offered
        assert extra.id in offered
        assert "Детейлер" in data["master_brief"]

    async def test_inspect_infers_tags_from_notes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_service: Service,
    ):
        resp = await client.post(
            "/api/ai/detailer/inspect",
            json={"notes": "мутные фары и сколы на капоте"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        tags = resp.json()["tags"]
        assert "chips" in tags
        assert "lights" in tags

    async def test_slots_skip_occupied_box(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
        test_service: Service,
        test_car,
        test_user,
        db_session,
        default_tenant,
    ):
        box_a = Box(name="Бокс A", tenant_id=default_tenant.id, sort_order=0, is_active=True)
        box_b = Box(name="Бокс B", tenant_id=default_tenant.id, sort_order=1, is_active=True)
        db_session.add_all([box_a, box_b])
        await db_session.commit()
        await db_session.refresh(box_a)
        await db_session.refresh(box_b)
        db_session.add(BoxService(
            box_id=box_a.id, service_id=test_service.id, tenant_id=default_tenant.id,
        ))
        await db_session.commit()

        start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        if start < datetime.now(timezone.utc):
            start = start + timedelta(days=1)
        busy = Appointment(
            tenant_id=default_tenant.id,
            client_id=test_user.id,
            car_id=test_car.id,
            service_id=test_service.id,
            box_id=box_a.id,
            start_time=start,
            end_time=start + timedelta(hours=2),
            status="confirmed",
            total_price=5000,
        )
        db_session.add(busy)
        await db_session.commit()

        date_str = start.date().isoformat()
        resp = await client.get(
            f"/api/ai/detailer/slots?service_id={test_service.id}&date={date_str}&tz_offset=0",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        assert items
        ten = next((s for s in items if s["time"] == "10:00"), None)
        assert ten is not None
        assert ten["available"] is True
        assert ten["box_id"] == box_b.id
        assert ten["free_boxes"] >= 1

    async def test_book_with_inspect_writes_master_brief(
        self,
        client: AsyncClient,
        auth_headers: dict,
        master_headers: dict,
        test_service: Service,
        test_car,
        test_master,
        db_session,
        default_tenant,
    ):
        box = Box(name="Бокс 1", tenant_id=default_tenant.id, sort_order=0, is_active=True)
        db_session.add(box)
        await db_session.commit()
        await db_session.refresh(box)

        inspect = await client.post(
            "/api/ai/detailer/inspect",
            json={"tags": ["chips"], "car_id": test_car.id},
            headers=auth_headers,
        )
        assert inspect.status_code == 200, inspect.text
        inspect_id = inspect.json()["id"]
        brief = inspect.json()["master_brief"]
        slot = inspect.json()["slots"][0] if inspect.json()["slots"] else None
        start_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        box_id = slot["box_id"] if slot else box.id
        if slot:
            start_time = slot["start_time"]

        resp = await client.post(
            "/api/appointments",
            json={
                "service_id": test_service.id,
                "car_id": test_car.id,
                "start_time": start_time,
                "box_id": box_id,
                "master_id": test_master.id,
                "inspect_id": inspect_id,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["master_brief"] == brief
        assert data["box_id"] == box_id

        master_resp = await client.get(
            f"/api/masters/me/appointments/{data['id']}/detailer-brief",
            headers=master_headers,
        )
        assert master_resp.status_code == 200, master_resp.text
        body = master_resp.json()
        assert body["inspect_id"] == inspect_id
        assert "Детейлер" in (body["master_brief"] or "")
        assert body["findings"]
