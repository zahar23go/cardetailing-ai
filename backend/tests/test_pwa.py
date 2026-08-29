"""PWA: манифест, splash, установка, офлайн записей."""

from httpx import AsyncClient

from app.modules.plans import PWA_DEFAULT_NAME, pwa_for_tenant, web_manifest


class TestPwa:
    async def test_default_manifest(self, client: AsyncClient):
        resp = await client.get("/api/pwa/manifest")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == PWA_DEFAULT_NAME
        assert data["display"] == "standalone"
        assert data["start_url"] == "/"
        assert any(i.get("src") for i in data["icons"])

    async def test_business_white_label(
        self,
        client: AsyncClient,
        default_tenant,
        db_session,
    ):
        default_tenant.plan = "business"
        default_tenant.name = "Gold Wash"
        await db_session.commit()
        resp = await client.get(f"/api/pwa/manifest?tenant={default_tenant.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Gold Wash"
        assert resp.json()["short_name"]

    async def test_basic_keeps_platform_name(
        self,
        client: AsyncClient,
        default_tenant,
        db_session,
    ):
        default_tenant.plan = "basic"
        default_tenant.name = "Gold Wash"
        await db_session.commit()
        resp = await client.get(f"/api/pwa/manifest?tenant={default_tenant.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == PWA_DEFAULT_NAME

    async def test_me_includes_pwa(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pwa" in data
        assert data["pwa"]["name"]
        assert "white_label" in data["pwa"]

    def test_pwa_helper_pro_not_white_label(self):
        class T:
            plan = "pro"
            name = "Salon X"
            logo_url = None
        assert pwa_for_tenant(T())["white_label"] is False
        assert pwa_for_tenant(T())["name"] == PWA_DEFAULT_NAME
        man = web_manifest(pwa_for_tenant(None))
        assert man["display"] == "standalone"
