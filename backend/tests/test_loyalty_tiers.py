"""Тесты уровней лояльности."""

from httpx import AsyncClient
from app.models import LoyaltyTierConfig


class TestLoyaltyTiers:
    """Тесты для программы лояльности."""

    async def test_create_tier_config(self, db_session, default_tenant):
        """✅ Создание конфигурации уровня."""
        cfg = LoyaltyTierConfig(
            tenant_id=default_tenant.id, tier="bronze",
            min_total_spent=0, min_visits=0,
            discount_percent=0, bonus_multiplier=1, color="#CD7F32",
        )
        db_session.add(cfg)
        await db_session.commit()
        assert cfg.id is not None

    async def test_get_tiers_endpoint(self, client, admin_headers, db_session, default_tenant):
        """✅ Получение списка уровней."""
        from app.models import LoyaltyTierConfig

        # Создаём конфиги через фикстуру сессии
        for t in [
            ("bronze", 0, 0, 0, 1, "#CD7F32"),
            ("silver", 30000, 5, 5, 2, "#C0C0C0"),
            ("gold", 100000, 20, 10, 3, "#FFD700"),
        ]:
            db_session.add(LoyaltyTierConfig(
                tenant_id=default_tenant.id,
                tier=t[0], min_total_spent=t[1], min_visits=t[2],
                discount_percent=t[3], bonus_multiplier=t[4], color=t[5],
            ))
        await db_session.commit()

        resp = await client.get("/api/loyalty/tiers", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    async def test_my_tier_endpoint(self, client, auth_headers):
        """✅ Получение своего уровня."""
        resp = await client.get("/api/loyalty/my-tier", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data
        assert "next_tier" in data

    async def test_update_tiers(self, client, admin_headers):
        """✅ Обновление конфигурации уровней."""
        tiers_data = [
            {"tier": "bronze", "min_total_spent": 0, "min_visits": 0,
             "discount_percent": 0, "bonus_multiplier": 1, "color": "#CD7F32"},
            {"tier": "silver", "min_total_spent": 20000, "min_visits": 3,
             "discount_percent": 5, "bonus_multiplier": 2, "color": "#C0C0C0"},
            {"tier": "gold", "min_total_spent": 80000, "min_visits": 15,
             "discount_percent": 10, "bonus_multiplier": 3, "color": "#FFD700"},
        ]
        resp = await client.put("/api/loyalty/tiers", json=tiers_data, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
