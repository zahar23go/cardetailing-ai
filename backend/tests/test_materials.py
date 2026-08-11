"""Тесты CRUD склада (Materials) — модуль «Технология»."""

from __future__ import annotations

import pytest
from uuid import UUID

from app.schemas import MaterialCreate, MaterialUpdate
from app.services import materials_service as svc


@pytest.mark.asyncio
class TestMaterialsCRUD:
    async def test_create_and_get(self, db_session, default_tenant):
        created = await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(
                name="Шампунь Koch Chemie",
                sku="KC-001",
                category="chemistry",
                unit="l",
                quantity=12.5,
                min_quantity=3,
                purchase_price=890,
                supplier="Detailing Pro",
            ),
        )
        assert created.id is not None
        assert created.name == "Шампунь Koch Chemie"

        got = await svc.get_material(db_session, default_tenant.id, created.id)
        assert got is not None
        assert float(got.quantity) == 12.5

        out = svc.material_to_out(got)
        assert out.is_low_stock is False
        assert out.stock_value == round(12.5 * 890, 2)

    async def test_list_filters_and_low_stock(self, db_session, default_tenant):
        await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(name="Микрофибра", category="consumables", unit="pcs", quantity=50, min_quantity=10),
        )
        await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(name="Полироль", category="chemistry", unit="ml", quantity=2, min_quantity=5),
        )

        items, total = await svc.list_materials(db_session, default_tenant.id)
        assert total == 2
        assert len(items) == 2

        chem, chem_total = await svc.list_materials(
            db_session, default_tenant.id, category="chemistry"
        )
        assert chem_total == 1
        assert chem[0].name == "Полироль"

        low, low_total = await svc.list_materials(
            db_session, default_tenant.id, low_stock_only=True
        )
        assert low_total == 1
        assert low[0].name == "Полироль"
        assert svc.material_to_out(low[0]).is_low_stock is True

    async def test_update_and_adjust_quantity(self, db_session, default_tenant):
        created = await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(name="Губка", category="inventory", quantity=10, purchase_price=100),
        )
        updated = await svc.update_material(
            db_session,
            default_tenant.id,
            created.id,
            MaterialUpdate(min_quantity=4, supplier="Local Store"),
        )
        assert updated is not None
        assert float(updated.min_quantity) == 4
        assert updated.supplier == "Local Store"

        adjusted = await svc.adjust_quantity(db_session, default_tenant.id, created.id, -3)
        assert float(adjusted.quantity) == 7

        # не уходим в минус
        adjusted = await svc.adjust_quantity(db_session, default_tenant.id, created.id, -100)
        assert float(adjusted.quantity) == 0

    async def test_delete_and_tenant_isolation(
        self, db_session, default_tenant, test_admin
    ):
        created = await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(name="Временный", category="other"),
        )
        ok = await svc.delete_material(db_session, default_tenant.id, created.id)
        assert ok is True
        assert await svc.get_material(db_session, default_tenant.id, created.id) is None

        # чужой tenant_id — не находим
        other_id = UUID("00000000-0000-0000-0000-000000000099")
        assert await svc.get_material(db_session, other_id, 1) is None

    async def test_search_by_name_and_sku(self, db_session, default_tenant):
        await svc.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(name="Керамика Gyeon", sku="GY-CER-50", category="chemistry"),
        )
        items, total = await svc.list_materials(db_session, default_tenant.id, search="gyeon")
        assert total == 1
        items, total = await svc.list_materials(db_session, default_tenant.id, search="GY-CER")
        assert total == 1

    async def test_category_catalog(self):
        cats = svc.list_category_items()
        keys = {c["key"] for c in cats}
        assert {"chemistry", "consumables", "inventory", "workwear", "other"} <= keys
