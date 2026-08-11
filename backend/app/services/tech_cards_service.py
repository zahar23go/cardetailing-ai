"""
CRUD техкарт (Tech Cards) — модуль «Технология».

Техкарта = услуга + список материалов с расходом на одну услугу.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Material, Service, TechCard, TechCardItem
from app.schemas import TechCardCreate, TechCardItemIn, TechCardItemOut, TechCardOut, TechCardUpdate


def _item_to_out(item: TechCardItem) -> TechCardItemOut:
    mat = item.material
    qty = float(item.quantity or 0)
    price = float(mat.purchase_price or 0) if mat else 0.0
    stock = float(mat.quantity or 0) if mat else 0.0
    min_qty = float(mat.min_quantity or 0) if mat else 0.0
    return TechCardItemOut(
        id=item.id,
        material_id=item.material_id,
        material_name=mat.name if mat else f"#{item.material_id}",
        material_unit=mat.unit if mat else "pcs",
        material_sku=mat.sku if mat else None,
        purchase_price=price,
        stock_quantity=stock,
        quantity=qty,
        line_cost=round(qty * price, 2),
        notes=item.notes,
        is_low_stock=stock <= min_qty,
    )


def tech_card_to_out(card: TechCard) -> TechCardOut:
    items = [_item_to_out(i) for i in (card.items or [])]
    cost = round(sum(i.line_cost for i in items), 2)
    svc = card.service
    display_name = card.name or (svc.name if svc else None)
    return TechCardOut(
        id=card.id,
        service_id=card.service_id,
        service_name=svc.name if svc else f"Услуга #{card.service_id}",
        service_price=float(svc.price or 0) if svc else 0.0,
        name=display_name,
        notes=card.notes,
        is_active=bool(card.is_active),
        items=items,
        items_count=len(items),
        estimated_cost=cost,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


def _card_query():
    return (
        select(TechCard)
        .options(
            selectinload(TechCard.service),
            selectinload(TechCard.items).selectinload(TechCardItem.material),
        )
    )


async def list_tech_cards(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    service_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[list[TechCard], int]:
    filters = [TechCard.tenant_id == tenant_id]
    if service_id is not None:
        filters.append(TechCard.service_id == service_id)
    if is_active is not None:
        filters.append(TechCard.is_active == is_active)

    need_service_join = bool(search and search.strip())
    count_stmt = select(func.count(TechCard.id)).where(*filters)
    if need_service_join:
        q = f"%{search.strip()}%"
        count_stmt = (
            select(func.count(TechCard.id))
            .join(Service, TechCard.service_id == Service.id)
            .where(*filters)
            .where((TechCard.name.ilike(q)) | (Service.name.ilike(q)))
        )
    total = int((await db.execute(count_stmt)).scalar() or 0)

    stmt = (
        _card_query()
        .join(Service, TechCard.service_id == Service.id)
        .where(*filters)
    )
    if need_service_join:
        q = f"%{search.strip()}%"
        stmt = stmt.where((TechCard.name.ilike(q)) | (Service.name.ilike(q)))

    result = await db.execute(
        stmt.order_by(Service.name.asc()).offset(skip).limit(limit)
    )
    return list(result.scalars().unique().all()), total


async def get_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
) -> TechCard | None:
    result = await db.execute(
        _card_query().where(
            TechCard.id == card_id,
            TechCard.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_service(db: AsyncSession, tenant_id: UUID, service_id: int) -> Service:
    result = await db.execute(
        select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id)
    )
    svc = result.scalar_one_or_none()
    if not svc:
        raise ValueError("Услуга не найдена")
    return svc


async def _validate_items(
    db: AsyncSession,
    tenant_id: UUID,
    items: list[TechCardItemIn],
) -> None:
    if not items:
        return
    ids = [i.material_id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Материал нельзя указать дважды в одной техкарте")
    result = await db.execute(
        select(Material.id).where(
            Material.tenant_id == tenant_id,
            Material.id.in_(ids),
        )
    )
    found = {row[0] for row in result.all()}
    missing = [mid for mid in ids if mid not in found]
    if missing:
        raise ValueError(f"Материалы не найдены: {missing}")


async def _replace_items(
    db: AsyncSession,
    card: TechCard,
    items: list[TechCardItemIn],
) -> None:
    old_result = await db.execute(
        select(TechCardItem).where(TechCardItem.tech_card_id == card.id)
    )
    for old in old_result.scalars().all():
        await db.delete(old)
    await db.flush()

    for row in items:
        db.add(
            TechCardItem(
                tech_card_id=card.id,
                material_id=row.material_id,
                quantity=row.quantity,
                notes=row.notes,
            )
        )
    await db.flush()
    db.expire(card, ["items"])


async def create_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    data: TechCardCreate,
) -> TechCard:
    await _ensure_service(db, tenant_id, data.service_id)
    await _validate_items(db, tenant_id, data.items)

    existing = await db.execute(
        select(TechCard.id).where(
            TechCard.tenant_id == tenant_id,
            TechCard.service_id == data.service_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Техкарта для этой услуги уже существует")

    card = TechCard(
        tenant_id=tenant_id,
        service_id=data.service_id,
        name=(data.name.strip() if data.name else None),
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(card)
    await db.flush()
    await _replace_items(db, card, data.items)
    await db.commit()

    created = await get_tech_card(db, tenant_id, card.id)
    assert created is not None
    return created


async def update_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    data: TechCardUpdate,
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None

    update_data = data.model_dump(exclude_unset=True, exclude={"items"})
    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip() or None
    for key, value in update_data.items():
        setattr(card, key, value)

    if data.items is not None:
        await _validate_items(db, tenant_id, data.items)
        await _replace_items(db, card, data.items)

    await db.commit()
    return await get_tech_card(db, tenant_id, card_id)


async def delete_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
) -> bool:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return False
    await db.delete(card)
    await db.commit()
    return True
