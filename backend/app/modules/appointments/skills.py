"""Навыки мастера: услуги/техкарты и комиссия в чеке."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MasterSkill, TechCard, User, UserRole


def _round2(value: float) -> float:
    return round(float(value or 0), 2)


def clamp_percent(value) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, n))


def commission_amount(price: float, percent: int) -> float:
    return _round2(float(price or 0) * clamp_percent(percent) / 100)


async def list_skills(db: AsyncSession, tenant_id: UUID, master_id: int) -> list[MasterSkill]:
    result = await db.execute(
        select(MasterSkill)
        .options(selectinload(MasterSkill.service))
        .where(
            MasterSkill.tenant_id == tenant_id,
            MasterSkill.master_id == master_id,
        )
        .order_by(MasterSkill.id)
    )
    return list(result.scalars().all())


async def master_can_do(
    db: AsyncSession,
    tenant_id: UUID,
    master_id: int | None,
    service_id: int | None,
) -> bool:
    if master_id is None or service_id is None:
        return True
    skills = await list_skills(db, tenant_id, master_id)
    if not skills:
        return True
    return any(s.service_id == service_id for s in skills)


async def resolve_commission(
    db: AsyncSession,
    tenant_id: UUID,
    master_id: int | None,
    service_id: int | None,
    price: float,
) -> tuple[int, float]:
    if not master_id:
        return 0, 0.0
    user = await db.get(User, master_id)
    default_pct = clamp_percent(getattr(user, "commission_percent", 0) if user else 0)
    if not service_id:
        return default_pct, commission_amount(price, default_pct)
    skills = await list_skills(db, tenant_id, master_id)
    for skill in skills:
        if skill.service_id == service_id:
            pct = clamp_percent(skill.commission_percent)
            return pct, commission_amount(price, pct)
    if skills:
        return 0, 0.0
    return default_pct, commission_amount(price, default_pct)


async def eligible_master_ids(
    db: AsyncSession,
    tenant_id: UUID,
    service_id: int | None,
    master_ids: list[int],
) -> set[int]:
    if not service_id or not master_ids:
        return set(master_ids)
    result = await db.execute(
        select(MasterSkill.master_id, MasterSkill.service_id).where(
            MasterSkill.tenant_id == tenant_id,
            MasterSkill.master_id.in_(master_ids),
        )
    )
    by_master: dict[int, set[int]] = {mid: set() for mid in master_ids}
    for mid, sid in result.all():
        by_master.setdefault(mid, set()).add(sid)
    allowed = set()
    for mid in master_ids:
        services = by_master.get(mid) or set()
        if not services or service_id in services:
            allowed.add(mid)
    return allowed


async def tech_card_service_ids(db: AsyncSession, tenant_id: UUID, service_ids: list[int]) -> set[int]:
    if not service_ids:
        return set()
    result = await db.execute(
        select(TechCard.service_id).where(
            TechCard.tenant_id == tenant_id,
            TechCard.service_id.in_(service_ids),
        )
    )
    return {row[0] for row in result.all() if row[0] is not None}


async def get_master_or_404(db: AsyncSession, tenant_id: UUID, master_id: int) -> User:
    result = await db.execute(
        select(User).where(
            User.id == master_id,
            User.tenant_id == tenant_id,
            User.role == UserRole.master.value,
        )
    )
    return result.scalar_one_or_none()
