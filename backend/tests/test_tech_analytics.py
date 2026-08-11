"""Тесты аналитики технологии: закупки и норма vs факт."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models import Appointment, Material, Service
from app.schemas import MaterialCreate, TechCardCreate, TechCardItemIn
from app.services import materials_service as mats
from app.services import tech_analytics_service as analytics
from app.services import tech_cards_service as cards


@pytest.mark.asyncio
class TestTechAnalytics:
    async def test_purchase_and_audit(
        self,
        db_session,
        default_tenant,
        test_user,
        test_car,
    ):
        service = Service(
            name="Мойка",
            description="t",
            category="Мойка",
            price=2000,
            duration=60,
            material_cost=100,
            cost_price=100,
            is_active=True,
            tenant_id=default_tenant.id,
        )
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)

        mat = await mats.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(
                name="Шампунь",
                category="chemistry",
                unit="ml",
                quantity=50,
                min_quantity=200,
                purchase_price=1,
            ),
        )
        await cards.create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=service.id,
                items=[TechCardItemIn(material_id=mat.id, quantity=100)],
            ),
        )

        now = datetime.now(timezone.utc)
        for _ in range(3):
            db_session.add(
                Appointment(
                    client_id=test_user.id,
                    car_id=test_car.id,
                    service_id=service.id,
                    tenant_id=default_tenant.id,
                    start_time=now - timedelta(days=1),
                    end_time=now - timedelta(days=1, hours=-1),
                    status="completed",
                    total_price=2000,
                )
            )
        await db_session.commit()

        # факт: приход +400, затем списание 400 (норма 3×100=300 → перерасход)
        await mats.adjust_quantity(db_session, default_tenant.id, mat.id, 400, reason="приход")
        await mats.adjust_quantity(db_session, default_tenant.id, mat.id, -400, reason="факт")

        buys = await analytics.purchase_recommendations(
            db_session, default_tenant.id, days=30, cover_days=30
        )
        assert any(r["material_id"] == mat.id and r["priority"] == "critical" for r in buys)
        assert any(r["recommend_qty"] > 0 for r in buys if r["material_id"] == mat.id)

        audit = await analytics.consumption_audit(db_session, default_tenant.id, days=30)
        row = next(r for r in audit if r["material_id"] == mat.id)
        assert row["norm_qty"] == 300
        assert row["fact_qty"] == 400
        assert row["status"] == "over"

        summary = await analytics.tech_analytics_summary(db_session, default_tenant.id)
        assert summary["purchase_critical"] >= 1
        assert summary["audit_overspend"] >= 1

    async def test_api(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
    ):
        mat = Material(
            name="Салфетка",
            category="consumables",
            unit="pcs",
            quantity=1,
            min_quantity=10,
            purchase_price=20,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()

        s = await client.get(
            "/api/tech-analytics/summary",
            headers=admin_headers,
        )
        assert s.status_code == 200
        assert "purchase_items" in s.json()

        p = await client.get(
            "/api/tech-analytics/purchase-recommendations",
            headers=admin_headers,
        )
        assert p.status_code == 200
        assert any(x["material_name"] == "Салфетка" for x in p.json())

        a = await client.get(
            "/api/tech-analytics/consumption-audit",
            headers=admin_headers,
        )
        assert a.status_code == 200
