"""LoyaltyService — расчёт уровней лояльности."""

from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LoyaltyPoints, LoyaltyTierConfig, Appointment


async def recalculate_tier(db: AsyncSession, client_id: int, tenant_id: UUID) -> str:
    """Пересчитать уровень клиента на основе потраченной суммы и визитов."""
    # Получаем статистику клиента
    lp_result = await db.execute(
        select(LoyaltyPoints).where(
            LoyaltyPoints.client_id == client_id,
            LoyaltyPoints.tenant_id == tenant_id,
        )
    )
    lp = lp_result.scalar_one_or_none()
    total_spent = lp.total_spent if lp else 0

    visits_result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.client_id == client_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        )
    )
    total_visits = visits_result.scalar() or 0

    # Получаем конфигурацию уровней
    config_result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == tenant_id)
        .order_by(LoyaltyTierConfig.min_total_spent.desc())
    )
    tiers = config_result.scalars().all()

    if not tiers:
        return "bronze"

    # Определяем уровень
    new_tier = "bronze"
    for t in tiers:
        if total_spent >= t.min_total_spent and total_visits >= t.min_visits:
            new_tier = t.tier
            break

    # Обновляем запись
    if lp:
        lp.tier = new_tier
        await db.commit()

    return new_tier


async def get_client_tier_info(db: AsyncSession, client_id: int, tenant_id: UUID) -> dict:
    """Получить информацию об уровне клиента."""
    lp_result = await db.execute(
        select(LoyaltyPoints).where(
            LoyaltyPoints.client_id == client_id,
            LoyaltyPoints.tenant_id == tenant_id,
        )
    )
    lp = lp_result.scalar_one_or_none()

    tier_name = lp.tier if lp else "bronze"
    total_spent = lp.total_spent if lp else 0

    visits_result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.client_id == client_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        )
    )
    total_visits = visits_result.scalar() or 0

    # Получаем следующий уровень
    config_result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == tenant_id)
        .order_by(LoyaltyTierConfig.min_total_spent.asc())
    )
    tiers = config_result.scalars().all()

    next_tier = None
    progress = 100.0
    remaining = 0

    for i, t in enumerate(tiers):
        if t.tier == tier_name and i + 1 < len(tiers):
            next_t = tiers[i + 1]
            next_tier = next_t.tier
            needed = next_t.min_total_spent - t.min_total_spent
            current = total_spent - t.min_total_spent
            progress = min(100.0, (current / needed) * 100) if needed > 0 else 100.0
            remaining = max(0, next_t.min_total_spent - total_spent)
            break

    return {
        "tier": tier_name,
        "total_spent": total_spent,
        "total_visits": total_visits,
        "points_balance": lp.balance if lp else 0,
        "next_tier": next_tier,
        "next_tier_progress": round(progress, 1),
        "next_tier_remaining": remaining,
    }
