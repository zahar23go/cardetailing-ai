"""Тесты учёта склада (Inventory)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Material
from app.schemas import MaterialCreate
from app.services import materials_service as mats
from app.services import inventory_service as inv


@pytest.mark.asyncio
class TestInventory:
    async def test_movements_and_abc(self, db_session, default_tenant):
        m = await mats.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(
                name="Химия A",
                category="chemistry",
                unit="l",
                quantity=10,
                min_quantity=2,
                purchase_price=100,
            ),
        )
        await mats.adjust_quantity(db_session, default_tenant.id, m.id, -3, reason="тест расход")
        await mats.adjust_quantity(db_session, default_tenant.id, m.id, 5, reason="тест приход")

        moves, total = await inv.list_movements(db_session, default_tenant.id)
        assert total >= 3  # initial + out + in

        hist = await inv.stock_history(db_session, default_tenant.id, material_id=m.id, days=7)
        assert len(hist) >= 1
        assert hist[-1]["quantity"] == 12  # 10 - 3 + 5

        abc = await inv.abc_analysis(db_session, default_tenant.id, days=30)
        assert any(r["material_id"] == m.id for r in abc)

        # сделаем критическим
        await mats.adjust_quantity(db_session, default_tenant.id, m.id, -20)
        crit = await inv.critical_positions(db_session, default_tenant.id)
        assert any(c["material_id"] == m.id for c in crit)

    async def test_api_endpoints(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
    ):
        mat = Material(
            name="API Mat",
            category="consumables",
            unit="pcs",
            quantity=1,
            min_quantity=5,
            purchase_price=10,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()

        summary = await client.get("/api/inventory/summary", headers=admin_headers)
        assert summary.status_code == 200
        assert "stock_value" in summary.json()

        moves = await client.get("/api/inventory/movements", headers=admin_headers)
        assert moves.status_code == 200

        hist = await client.get("/api/inventory/stock-history?days=14", headers=admin_headers)
        assert hist.status_code == 200

        abc = await client.get("/api/inventory/abc", headers=admin_headers)
        assert abc.status_code == 200

        crit = await client.get("/api/inventory/critical", headers=admin_headers)
        assert crit.status_code == 200
        assert any(x["material_name"] == "API Mat" for x in crit.json())
