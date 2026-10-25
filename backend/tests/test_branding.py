"""White Label: брендинг хранится в тенанте, а не в браузере."""
import base64

from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models import Tenant

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


async def _tenant(db_session, tenant_id) -> Tenant:
    return (
        await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one()


class TestBranding:
    async def test_defaults_for_client(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/branding", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["accent_solid"] == "#D4AF37"
        assert data["base_theme"] == "goldMetal"
        assert data["surface_mode"] == "light"
        assert data["name"] == "Test Workshop"

    async def test_admin_saves_branding_to_tenant(
        self, client: AsyncClient, admin_headers: dict, db_session, default_tenant
    ):
        payload = {
            "accent_solid": "#1122aa",
            "radius_md": "20px",
            "font_ui": "Inter, sans-serif",
            "base_theme": "goldGlow",
            "surface_mode": "dark",
        }
        resp = await client.put("/api/branding", json=payload, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["accent_solid"] == "#1122AA"
        assert data["surface_mode"] == "dark"

        tenant = await _tenant(db_session, default_tenant.id)
        assert tenant.config["branding"]["accent_solid"] == "#1122AA"
        assert tenant.config["branding"]["base_theme"] == "goldGlow"

        again = await client.get("/api/branding", headers=admin_headers)
        assert again.json()["accent_solid"] == "#1122AA"

    async def test_admin_can_set_logo_url(
        self, client: AsyncClient, admin_headers: dict, db_session, default_tenant
    ):
        resp = await client.put(
            "/api/branding",
            json={"logo_url": "/uploads/branding/logo.png"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["logo_url"] == "/uploads/branding/logo.png"
        tenant = await _tenant(db_session, default_tenant.id)
        assert tenant.logo_url == "/uploads/branding/logo.png"

    async def test_client_cannot_edit(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/branding", json={"accent_solid": "#000000"}, headers=auth_headers
        )
        assert resp.status_code == 403

    async def test_invalid_accent_rejected(self, client: AsyncClient, admin_headers: dict):
        resp = await client.put(
            "/api/branding", json={"accent_solid": "red"}, headers=admin_headers
        )
        assert resp.status_code == 422

        resp = await client.put(
            "/api/branding", json={"radius_md": "999px"}, headers=admin_headers
        )
        assert resp.status_code == 422

    async def test_branding_requires_business_plan(
        self, client: AsyncClient, admin_headers: dict, db_session, default_tenant
    ):
        tenant = await _tenant(db_session, default_tenant.id)
        tenant.plan = "pro"
        await db_session.commit()

        resp = await client.put(
            "/api/branding", json={"accent_solid": "#000000"}, headers=admin_headers
        )
        assert resp.status_code == 403
        assert "Бизнес" in resp.json()["detail"]

        # Читать брендинг можно на любом тарифе.
        assert (await client.get("/api/branding", headers=admin_headers)).status_code == 200

    async def test_logo_upload(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
        monkeypatch,
        tmp_path,
    ):
        monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
        resp = await client.post(
            "/api/branding/logo",
            files={"file": ("logo.png", PNG_1X1, "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        logo_url = resp.json()["logo_url"]
        assert logo_url.startswith("/uploads/branding/")

        tenant = await _tenant(db_session, default_tenant.id)
        assert tenant.logo_url == logo_url
        assert (tmp_path / "branding" / logo_url.rsplit("/", 1)[-1]).exists()

    async def test_logo_upload_rejects_non_image(
        self, client: AsyncClient, admin_headers: dict, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
        resp = await client.post(
            "/api/branding/logo",
            files={"file": ("logo.png", b"not an image", "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 400
