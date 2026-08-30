"""Приёмка и ревизия склада с подписью."""

import pytest
from sqlalchemy import select

from app.models import Material, MaterialMovement
from app.schemas import MaterialCreate
from app.services import materials_service as mats


@pytest.mark.asyncio
class TestStockDocuments:
    async def test_intake_and_revision(
        self, client, admin_headers, db_session, default_tenant, test_admin,
    ):
        mat = await mats.create_material(
            db_session,
            default_tenant.id,
            MaterialCreate(
                name="Шампунь приёмка",
                category="chemistry",
                unit="ml",
                quantity=100,
                min_quantity=10,
                purchase_price=1.5,
            ),
        )

        bad = await client.post(
            "/api/inventory/intake",
            json={
                "signed_name": "не то имя",
                "document_no": "ПН-1",
                "lines": [{"material_id": mat.id, "qty": 40}],
            },
            headers=admin_headers,
        )
        assert bad.status_code == 400

        intake = await client.post(
            "/api/inventory/intake",
            json={
                "signed_name": test_admin.full_name,
                "document_no": "ПН-1",
                "note": "Поставка",
                "lines": [{"material_id": mat.id, "qty": 40}],
            },
            headers=admin_headers,
        )
        assert intake.status_code == 200, intake.text
        body = intake.json()
        assert body["doc_type"] == "intake"
        assert body["signed_name"] == test_admin.full_name
        assert body["lines"][0]["qty"] == 40
        assert body["lines"][0]["delta"] == 40

        await db_session.refresh(mat)
        assert float(mat.quantity) == 140

        rev = await client.post(
            "/api/inventory/revision",
            json={
                "signed_name": test_admin.full_name,
                "note": "Ревизия августа",
                "lines": [{"material_id": mat.id, "qty": 120}],
            },
            headers=admin_headers,
        )
        assert rev.status_code == 200, rev.text
        assert rev.json()["doc_type"] == "revision"
        assert rev.json()["lines"][0]["delta"] == -20

        await db_session.refresh(mat)
        assert float(mat.quantity) == 120

        moves = (
            await db_session.execute(
                select(MaterialMovement)
                .where(MaterialMovement.material_id == mat.id)
                .order_by(MaterialMovement.id)
            )
        ).scalars().all()
        types = [m.movement_type for m in moves]
        assert "in" in types
        assert "revision" in types
        assert any(m.document_id == intake.json()["id"] for m in moves)

        listed = await client.get("/api/inventory/documents", headers=admin_headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 2

    async def test_client_forbidden(self, client, auth_headers):
        resp = await client.post(
            "/api/inventory/intake",
            json={"signed_name": "x", "lines": [{"material_id": 1, "qty": 1}]},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    async def test_adjust_still_works(
        self, client, admin_headers, db_session, default_tenant,
    ):
        mat = Material(
            name="Для ±",
            category="other",
            unit="pcs",
            quantity=5,
            min_quantity=0,
            purchase_price=1,
            tenant_id=default_tenant.id,
        )
        db_session.add(mat)
        await db_session.commit()
        await db_session.refresh(mat)

        resp = await client.post(
            f"/api/materials/{mat.id}/adjust?delta=2",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 7
