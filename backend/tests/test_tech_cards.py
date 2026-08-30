"""Тесты техкарт (услуга → материалы)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Material, Service
from app.schemas import TechCardCreate, TechCardItemIn, TechCardUpdate
from app.services import tech_cards_service as svc


@pytest.mark.asyncio
class TestTechCardsCRUD:
    async def _seed(self, db_session, default_tenant):
        service = Service(
            name="Полировка",
            description="test",
            category="Детейлинг",
            price=8000,
            duration=120,
            material_cost=500,
            cost_price=500,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        mat = Material(
            name="Полироль",
            category="chemistry",
            unit="ml",
            quantity=1000,
            min_quantity=100,
            purchase_price=2.5,
            tenant_id=default_tenant.id,
        )
        db_session.add_all([service, mat])
        await db_session.commit()
        await db_session.refresh(service)
        await db_session.refresh(mat)
        return service, mat

    async def test_create_list_update_delete(self, db_session, default_tenant):
        service, mat = await self._seed(db_session, default_tenant)
        card = await svc.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=service.id,
                name="ТК Полировка",
                items=[TechCardItemIn(material_id=mat.id, quantity=50)],
            ),
        )
        out = svc.tech_card_to_out(card)
        assert out.items_count == 1
        assert out.estimated_cost == 125.0  # 50 * 2.5

        items, total = await svc.list_tech_cards(db_session, default_tenant.id)
        assert total == 1
        assert items[0].id == card.id

        updated = await svc.update_tech_card(
            db_session,
            default_tenant.id,
            card.id,
            TechCardUpdate(items=[TechCardItemIn(material_id=mat.id, quantity=100)]),
        )
        assert svc.tech_card_to_out(updated).estimated_cost == 250.0

        assert await svc.delete_tech_card(db_session, default_tenant.id, card.id) is True
        assert await svc.get_tech_card(db_session, default_tenant.id, card.id) is None

    async def test_duplicate_service_rejected(self, db_session, default_tenant):
        service, mat = await self._seed(db_session, default_tenant)
        await svc.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=service.id,
                items=[TechCardItemIn(material_id=mat.id, quantity=10)],
            ),
        )
        with pytest.raises(ValueError, match="уже существует"):
            await svc.create_tech_card(
                db_session,
                default_tenant.id,
                TechCardCreate(
                    service_id=service.id,
                    items=[TechCardItemIn(material_id=mat.id, quantity=5)],
                ),
            )


@pytest.mark.asyncio
class TestTechCardsAPI:
    async def test_api_flow(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
        test_service,
    ):
        mat = Material(
            name="Шампунь API",
            category="chemistry",
            unit="l",
            quantity=20,
            purchase_price=100,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        created = await client.post(
            "/api/tech-cards",
            headers=admin_headers,
            json={
                "service_id": test_service.id,
                "name": "ТК API",
                "items": [{"material_id": mat.id, "quantity": 0.5}],
            },
        )
        assert created.status_code == 201, created.text
        card_id = created.json()["id"]
        assert created.json()["estimated_cost"] == 50.0

        listed = await client.get("/api/tech-cards", headers=admin_headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        one = await client.get(f"/api/tech-cards/{card_id}", headers=admin_headers)
        assert one.status_code == 200
        assert one.json()["service_id"] == test_service.id

        deleted = await client.delete(f"/api/tech-cards/{card_id}", headers=admin_headers)
        assert deleted.status_code == 200

    async def test_blocks_instruction_and_legacy_items(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
        test_service,
    ):
        shampoo = Material(
            name="Шампунь Koch",
            category="chemistry",
            unit="ml",
            quantity=1000,
            purchase_price=1,
            tenant_id=default_tenant.id,
        )
        water = Material(
            name="Вода",
            category="other",
            unit="l",
            quantity=100,
            purchase_price=0,
            tenant_id=default_tenant.id,
        )
        db_session.add_all([shampoo, water])
        await db_session.commit()
        await db_session.refresh(shampoo)
        await db_session.refresh(water)

        created = await client.post(
            "/api/tech-cards",
            headers=admin_headers,
            json={
                "service_id": test_service.id,
                "name": "Мойка кузова с воском",
                "blocks": [
                    {
                        "title": "Подготовка шампуня",
                        "description": "Развести 50 мл шампуня в 10 л воды",
                        "duration_minutes": 1,
                        "items": [
                            {"material_id": shampoo.id, "quantity": 50},
                            {"material_id": water.id, "quantity": 10},
                        ],
                    },
                    {
                        "title": "Нанесение пены",
                        "description": "Нанести пену снизу вверх",
                        "duration_minutes": 4,
                        "items": [{"material_id": shampoo.id, "quantity": 200}],
                    },
                    {
                        "title": "Смывка",
                        "description": "Смыть пену сверху вниз",
                        "duration_minutes": 2,
                        "items": [{"material_id": water.id, "quantity": 20}],
                    },
                ],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        card_id = body["id"]
        assert body["blocks_count"] == 3
        assert body["total_duration_minutes"] == 7
        assert body["items_count"] == 2  # агрегат: шампунь + вода
        shampoo_row = next(i for i in body["items"] if i["material_id"] == shampoo.id)
        assert shampoo_row["quantity"] == 250.0  # 50 + 200

        added = await client.post(
            f"/api/tech-cards/{card_id}/blocks",
            headers=admin_headers,
            json={"title": "Сушка", "duration_minutes": 3, "items": []},
        )
        assert added.status_code == 201, added.text
        assert added.json()["blocks_count"] == 4
        assert added.json()["total_duration_minutes"] == 10

        ids = [b["id"] for b in added.json()["blocks"]]
        reordered = await client.put(
            f"/api/tech-cards/{card_id}/blocks/reorder",
            headers=admin_headers,
            json={"block_ids": list(reversed(ids))},
        )
        assert reordered.status_code == 200, reordered.text
        assert [b["id"] for b in reordered.json()["blocks"]] == list(reversed(ids))

        first_id = reordered.json()["blocks"][0]["id"]
        deleted_block = await client.delete(
            f"/api/tech-cards/{card_id}/blocks/{first_id}",
            headers=admin_headers,
        )
        assert deleted_block.status_code == 200
        assert deleted_block.json()["blocks_count"] == 3

        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (2, 2), color="white").save(buf, format="PNG")
        photo = await client.post(
            "/api/tech-cards/upload-photo",
            headers=admin_headers,
            files={"file": ("step.png", buf.getvalue(), "image/png")},
        )
        assert photo.status_code == 200, photo.text
        assert photo.json()["url"].startswith("/uploads/tech-cards/")

        await client.delete(f"/api/tech-cards/{card_id}", headers=admin_headers)


@pytest.mark.asyncio
class TestTechCardVersionsPdf:
    async def test_versions_and_pdf(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
        test_service,
    ):
        mat = Material(
            name="Воск",
            category="chemistry",
            unit="ml",
            quantity=500,
            purchase_price=3,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        created = await client.post(
            "/api/tech-cards",
            headers=admin_headers,
            json={
                "service_id": test_service.id,
                "name": "ТК версии",
                "blocks": [{
                    "title": "Нанесение",
                    "description": "Нанести тонкий слой",
                    "duration_minutes": 5,
                    "items": [{"material_id": mat.id, "quantity": 20}],
                }],
            },
        )
        assert created.status_code == 201, created.text
        card_id = created.json()["id"]
        assert created.json()["current_version"] == 1

        listed = await client.get(f"/api/tech-cards/{card_id}/versions", headers=admin_headers)
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["version_no"] == 1

        updated = await client.put(
            f"/api/tech-cards/{card_id}",
            headers=admin_headers,
            json={
                "blocks": [{
                    "title": "Нанесение",
                    "description": "Нанести тонкий слой",
                    "duration_minutes": 5,
                    "items": [{"material_id": mat.id, "quantity": 40}],
                }],
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["current_version"] == 2

        v1 = await client.get(f"/api/tech-cards/{card_id}/versions/1", headers=admin_headers)
        assert v1.status_code == 200
        assert v1.json()["snapshot"]["items"][0]["quantity"] == 20

        pdf = await client.get(f"/api/tech-cards/{card_id}/pdf", headers=admin_headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content[:4] == b"%PDF"

        pdf_v1 = await client.get(f"/api/tech-cards/{card_id}/pdf?version=1", headers=admin_headers)
        assert pdf_v1.status_code == 200
        assert pdf_v1.content[:4] == b"%PDF"
