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
