"""API-тесты /api/materials (модуль «Технология» / Склад)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMaterialsAPI:
    async def test_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/materials")
        assert resp.status_code in (401, 403)

    async def test_categories(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/materials/categories", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        keys = {c["key"] for c in data}
        assert "chemistry" in keys
        assert "consumables" in keys

    async def test_crud_flow(self, client: AsyncClient, admin_headers: dict):
        # create
        create = await client.post(
            "/api/materials",
            headers=admin_headers,
            json={
                "name": "Шампунь API",
                "sku": "API-001",
                "category": "chemistry",
                "unit": "l",
                "quantity": 10,
                "min_quantity": 3,
                "purchase_price": 500,
                "supplier": "Test Supplier",
            },
        )
        assert create.status_code == 201
        item = create.json()
        mid = item["id"]
        assert item["name"] == "Шампунь API"
        assert item["is_low_stock"] is False
        assert item["stock_value"] == 5000.0

        # list
        listed = await client.get("/api/materials", headers=admin_headers)
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] >= 1
        assert any(x["id"] == mid for x in body["items"])

        # get by id
        one = await client.get(f"/api/materials/{mid}", headers=admin_headers)
        assert one.status_code == 200
        assert one.json()["sku"] == "API-001"

        # update
        upd = await client.put(
            f"/api/materials/{mid}",
            headers=admin_headers,
            json={"min_quantity": 12},
        )
        assert upd.status_code == 200
        assert upd.json()["is_low_stock"] is True

        # adjust
        adj = await client.post(
            f"/api/materials/{mid}/adjust?delta=5",
            headers=admin_headers,
        )
        assert adj.status_code == 200
        assert adj.json()["quantity"] == 15
        assert adj.json()["is_low_stock"] is False

        # search
        search = await client.get(
            "/api/materials?search=API-001",
            headers=admin_headers,
        )
        assert search.status_code == 200
        assert search.json()["total"] >= 1

        # delete
        deleted = await client.delete(f"/api/materials/{mid}", headers=admin_headers)
        assert deleted.status_code == 200
        missing = await client.get(f"/api/materials/{mid}", headers=admin_headers)
        assert missing.status_code == 404

    async def test_validation_bad_category(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/materials",
            headers=admin_headers,
            json={"name": "X", "category": "unknown"},
        )
        assert resp.status_code == 422
