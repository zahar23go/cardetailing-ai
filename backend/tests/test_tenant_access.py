"""P0: платформенный CRUD тенантов доступен только super_admin.

Обычный admin салона не должен ни видеть чужие тенанты, ни создавать,
ни менять, ни удалять их. Для переименования своего салона есть
отдельный self-service endpoint PUT /api/tenant/me.
"""

from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_token
from app.models import Tenant, User


@pytest_asyncio.fixture
async def foreign_tenant(db_session: AsyncSession) -> Tenant:
    """Второй салон, к которому обычный admin не должен иметь доступа."""
    tenant = Tenant(
        id=uuid4(),
        name="Foreign Salon",
        subdomain="foreign",
        config={},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def super_admin_headers(
    db_session: AsyncSession,
    test_admin: User,
    default_tenant: Tenant,
) -> dict:
    """Заголовки того же пользователя, но с ролью super_admin."""
    test_admin.role = "super_admin"
    await db_session.commit()
    token = create_token(test_admin.id, str(default_tenant.id))
    return {"Authorization": f"Bearer {token}"}


class TestTenantAccessForRegularAdmin:
    async def test_admin_cannot_list_tenants(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        resp = await client.get("/api/tenants", headers=admin_headers)
        assert resp.status_code == 403

    async def test_admin_cannot_create_tenant(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        resp = await client.post(
            "/api/tenants",
            json={"name": "Hacked Salon", "subdomain": "hacked"},
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_admin_cannot_read_foreign_tenant(
        self,
        client: AsyncClient,
        admin_headers: dict,
        foreign_tenant: Tenant,
    ):
        resp = await client.get(
            f"/api/tenants/{foreign_tenant.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_admin_cannot_read_own_tenant_via_platform_route(
        self,
        client: AsyncClient,
        admin_headers: dict,
        default_tenant: Tenant,
    ):
        """Даже свой тенант читается только через self-service endpoint."""
        resp = await client.get(
            f"/api/tenants/{default_tenant.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_admin_cannot_update_foreign_tenant(
        self,
        client: AsyncClient,
        admin_headers: dict,
        foreign_tenant: Tenant,
        db_session: AsyncSession,
    ):
        resp = await client.put(
            f"/api/tenants/{foreign_tenant.id}",
            json={"name": "Hijacked Salon"},
            headers=admin_headers,
        )
        assert resp.status_code == 403

        await db_session.refresh(foreign_tenant)
        assert foreign_tenant.name == "Foreign Salon"

    async def test_admin_cannot_delete_foreign_tenant(
        self,
        client: AsyncClient,
        admin_headers: dict,
        foreign_tenant: Tenant,
        db_session: AsyncSession,
    ):
        resp = await client.delete(
            f"/api/tenants/{foreign_tenant.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 403

        await db_session.refresh(foreign_tenant)
        assert foreign_tenant.name == "Foreign Salon"

    async def test_admin_cannot_change_plan(
        self,
        client: AsyncClient,
        admin_headers: dict,
        default_tenant: Tenant,
    ):
        resp = await client.put(
            f"/api/tenants/{default_tenant.id}/plan",
            json={"plan": "basic"},
            headers=admin_headers,
        )
        assert resp.status_code == 403

    async def test_client_cannot_access_tenants(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        resp = await client.get("/api/tenants", headers=auth_headers)
        assert resp.status_code == 403


class TestTenantSelfServiceAndSuperAdmin:
    async def test_admin_can_rename_own_tenant(
        self,
        client: AsyncClient,
        admin_headers: dict,
        default_tenant: Tenant,
        db_session: AsyncSession,
    ):
        resp = await client.put(
            "/api/tenant/me",
            json={"name": "  My Detailing Salon  "},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "My Detailing Salon"

        await db_session.refresh(default_tenant)
        assert default_tenant.name == "My Detailing Salon"

    async def test_super_admin_can_manage_tenants(
        self,
        client: AsyncClient,
        super_admin_headers: dict,
        foreign_tenant: Tenant,
    ):
        # Список и чтение
        listed = await client.get("/api/tenants", headers=super_admin_headers)
        assert listed.status_code == 200, listed.text
        ids = {item["id"] for item in listed.json()["items"]}
        assert str(foreign_tenant.id) in ids

        read = await client.get(
            f"/api/tenants/{foreign_tenant.id}",
            headers=super_admin_headers,
        )
        assert read.status_code == 200, read.text

        # Обновление
        updated = await client.put(
            f"/api/tenants/{foreign_tenant.id}",
            json={"name": "Renamed Foreign Salon"},
            headers=super_admin_headers,
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == "Renamed Foreign Salon"

        # Создание
        created = await client.post(
            "/api/tenants",
            json={"name": "Third Salon", "subdomain": "third"},
            headers=super_admin_headers,
        )
        assert created.status_code == 200, created.text
        assert created.json()["subdomain"] == "third"

        # Удаление
        deleted = await client.delete(
            f"/api/tenants/{foreign_tenant.id}",
            headers=super_admin_headers,
        )
        assert deleted.status_code == 200, deleted.text

        after = await client.get(
            f"/api/tenants/{foreign_tenant.id}",
            headers=super_admin_headers,
        )
        assert after.status_code == 404
