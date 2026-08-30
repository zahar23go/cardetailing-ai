"""Демо-пак 6 техкарт заказчика: склад + шаги + нормы."""

from sqlalchemy import select

from app.models import Material, TechCard
from app.modules.tech_cards.demo_pack import MARKER, apply_demo_pack
from app.modules.tech_cards.service import get_tech_card
from app.modules.tech_cards.service import tech_card_to_out


class TestDemoTechPack:
    async def test_applies_six_cards_and_is_idempotent(self, db_session, default_tenant):
        stats = await apply_demo_pack(db_session, default_tenant.id)
        await db_session.commit()
        assert stats["materials"] >= 20
        assert stats["created"] == 6
        assert stats["skipped"] == 0

        again = await apply_demo_pack(db_session, default_tenant.id)
        await db_session.commit()
        assert again["created"] == 0
        assert again["updated"] == 6

        foam = (
            await db_session.execute(
                select(Material).where(
                    Material.tenant_id == default_tenant.id,
                    Material.name == "Шампунь активная пена",
                )
            )
        ).scalar_one()
        assert foam.unit == "ml"
        assert float(foam.purchase_price) == 0.5

        cards = (
            await db_session.execute(
                select(TechCard).where(TechCard.tenant_id == default_tenant.id)
            )
        ).scalars().all()
        assert len(cards) == 6
        assert all(MARKER in (c.notes or "") for c in cards)

        wash = next(c for c in cards if c.name and "мойка" in c.name.lower() and "комплекс" not in c.name.lower())
        out = tech_card_to_out(await get_tech_card(db_session, default_tenant.id, wash.id))
        foam_lines = [i for i in out.items if i.material_name == "Шампунь активная пена"]
        assert foam_lines
        assert foam_lines[0].quantity == 50
        assert out.total_duration_minutes >= 10
        assert out.blocks_count >= 4
        assert "пеногенератор" in (out.notes or "").lower()
        assert out.estimated_cost > 0

    async def test_skips_non_demo_card_unless_forced(self, db_session, default_tenant):
        from app.models import Service
        from app.modules.tech_cards.service import create_tech_card
        from app.schemas import TechCardBlockIn, TechCardCreate

        svc = Service(
            tenant_id=default_tenant.id,
            name="Мойка кузова",
            description="своя",
            category="Мойка",
            price=1500,
            duration=20,
            material_cost=0,
            is_active=True,
        )
        db_session.add(svc)
        await db_session.flush()
        await create_tech_card(
            db_session,
            default_tenant.id,
            TechCardCreate(
                service_id=svc.id,
                name="Своя мойка",
                notes="ручная карта",
                is_active=True,
                blocks=[
                    TechCardBlockIn(
                        title="Свой шаг",
                        duration_minutes=5,
                        description="не трогать",
                        items=[],
                    )
                ],
            ),
        )
        await db_session.commit()

        stats = await apply_demo_pack(db_session, default_tenant.id)
        await db_session.commit()
        assert stats["skipped"] == 1
        assert stats["created"] == 5

        forced = await apply_demo_pack(db_session, default_tenant.id, force=True)
        await db_session.commit()
        assert forced["skipped"] == 0
        assert forced["updated"] >= 1

        cards = (
            await db_session.execute(
                select(TechCard).where(TechCard.tenant_id == default_tenant.id)
            )
        ).scalars().all()
        wash = next(c for c in cards if c.service_id == svc.id)
        assert MARKER in (wash.notes or "")
        assert wash.name == "Бесконтактная мойка кузова"
