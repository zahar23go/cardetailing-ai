"""
CRUD техкарт (Tech Cards) — модуль «Технология».

Техкарта = услуга + блоки-шаги (инструкция, материалы, фото, длительность).
Плоский список items сохраняется как агрегированный BOM (аналитика / старый API).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Material, Service, TechCard, TechCardBlock, TechCardItem
from app.schemas import (
    TechCardBlockIn,
    TechCardBlockOut,
    TechCardCreate,
    TechCardItemIn,
    TechCardItemOut,
    TechCardOut,
    TechCardUpdate,
)


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


def _aggregate_items(items: list[TechCardItemOut]) -> list[TechCardItemOut]:
    by_mat: dict[int, TechCardItemOut] = {}
    for it in items:
        prev = by_mat.get(it.material_id)
        if prev is None:
            by_mat[it.material_id] = it
            continue
        qty = prev.quantity + it.quantity
        by_mat[it.material_id] = prev.model_copy(update={
            "quantity": qty,
            "line_cost": round(qty * prev.purchase_price, 2),
        })
    return list(by_mat.values())


def _block_to_out(block: TechCardBlock) -> TechCardBlockOut:
    items = [_item_to_out(i) for i in (block.items or [])]
    cost = round(sum(i.line_cost for i in items), 2)
    return TechCardBlockOut(
        id=block.id,
        sort_order=int(block.sort_order or 0),
        title=block.title,
        description=block.description,
        duration_minutes=int(block.duration_minutes or 0),
        photo_url=block.photo_url,
        items=items,
        items_count=len(items),
        estimated_cost=cost,
    )


def tech_card_to_out(card: TechCard) -> TechCardOut:
    blocks = [_block_to_out(b) for b in (card.blocks or [])]
    if blocks:
        line_items = [it for b in blocks for it in b.items]
    else:
        line_items = [_item_to_out(i) for i in (card.items or [])]
        if line_items:
            blocks = [TechCardBlockOut(
                id=0,
                sort_order=0,
                title="Материалы",
                description=card.notes,
                duration_minutes=0,
                photo_url=None,
                items=line_items,
                items_count=len(line_items),
                estimated_cost=round(sum(i.line_cost for i in line_items), 2),
            )]

    items = _aggregate_items(line_items)
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
        blocks=blocks,
        blocks_count=len(blocks),
        total_duration_minutes=sum(b.duration_minutes for b in blocks),
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


def _card_query():
    return (
        select(TechCard)
        .options(
            selectinload(TechCard.service),
            selectinload(TechCard.blocks).selectinload(TechCardBlock.items).selectinload(TechCardItem.material),
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
    *,
    populate_existing: bool = False,
) -> TechCard | None:
    stmt = _card_query().where(
        TechCard.id == card_id,
        TechCard.tenant_id == tenant_id,
    )
    if populate_existing:
        stmt = stmt.execution_options(populate_existing=True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _reload_card(db: AsyncSession, tenant_id: UUID, card_id: int) -> TechCard:
    await db.commit()
    reloaded = await get_tech_card(db, tenant_id, card_id, populate_existing=True)
    assert reloaded is not None
    return reloaded


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
    *,
    allow_duplicates: bool = False,
) -> None:
    if not items:
        return
    ids = [i.material_id for i in items]
    if not allow_duplicates and len(ids) != len(set(ids)):
        raise ValueError("Материал нельзя указать дважды в одном блоке")
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


async def _validate_blocks(
    db: AsyncSession,
    tenant_id: UUID,
    blocks: list[TechCardBlockIn],
) -> None:
    all_items: list[TechCardItemIn] = []
    for block in blocks:
        title = (block.title or "").strip()
        if not title:
            raise ValueError("У блока должно быть название")
        ids = [i.material_id for i in block.items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"В блоке «{title}» материал указан дважды")
        all_items.extend(block.items)
    await _validate_items(db, tenant_id, all_items, allow_duplicates=True)


async def _clear_composition(db: AsyncSession, card: TechCard) -> None:
    old_blocks = (
        await db.execute(select(TechCardBlock).where(TechCardBlock.tech_card_id == card.id))
    ).scalars().all()
    for old in old_blocks:
        await db.delete(old)
    await db.flush()
    leftover = (
        await db.execute(select(TechCardItem).where(TechCardItem.tech_card_id == card.id))
    ).scalars().all()
    for old in leftover:
        await db.delete(old)
    await db.flush()


async def _replace_blocks(
    db: AsyncSession,
    card: TechCard,
    blocks: list[TechCardBlockIn],
) -> None:
    await _clear_composition(db, card)
    for idx, row in enumerate(blocks):
        block = TechCardBlock(
            tech_card_id=card.id,
            sort_order=idx,
            title=row.title.strip(),
            description=(row.description.strip() if row.description else None),
            duration_minutes=int(row.duration_minutes or 0),
            photo_url=row.photo_url or None,
        )
        db.add(block)
        await db.flush()
        for item in row.items:
            db.add(
                TechCardItem(
                    tech_card_id=card.id,
                    block_id=block.id,
                    material_id=item.material_id,
                    quantity=item.quantity,
                    notes=item.notes,
                )
            )
    await db.flush()
    db.expire(card, ["items", "blocks"])


async def _replace_items(
    db: AsyncSession,
    card: TechCard,
    items: list[TechCardItemIn],
) -> None:
    await _replace_blocks(
        db,
        card,
        [TechCardBlockIn(title="Материалы", items=items)],
    )


def _blocks_from_payload(data: TechCardCreate | TechCardUpdate) -> list[TechCardBlockIn] | None:
    blocks = getattr(data, "blocks", None)
    items = getattr(data, "items", None)
    if blocks:
        return list(blocks)
    if items:
        return [TechCardBlockIn(title="Материалы", items=list(items))]
    return None


async def create_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    data: TechCardCreate,
) -> TechCard:
    await _ensure_service(db, tenant_id, data.service_id)

    existing = await db.execute(
        select(TechCard.id).where(
            TechCard.tenant_id == tenant_id,
            TechCard.service_id == data.service_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Техкарта для этой услуги уже существует")

    blocks = _blocks_from_payload(data) or []
    if blocks:
        await _validate_blocks(db, tenant_id, blocks)

    card = TechCard(
        tenant_id=tenant_id,
        service_id=data.service_id,
        name=(data.name.strip() if data.name else None),
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(card)
    await db.flush()
    if blocks:
        await _replace_blocks(db, card, blocks)
    return await _reload_card(db, tenant_id, card.id)


async def update_tech_card(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    data: TechCardUpdate,
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None

    update_data = data.model_dump(exclude_unset=True, exclude={"items", "blocks"})
    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip() or None
    for key, value in update_data.items():
        setattr(card, key, value)

    payload = data.model_dump(exclude_unset=True)
    if "blocks" in payload:
        blocks = list(data.blocks or [])
        await _validate_blocks(db, tenant_id, blocks)
        await _replace_blocks(db, card, blocks)
    elif "items" in payload and data.items is not None:
        await _validate_items(db, tenant_id, data.items)
        await _replace_items(db, card, data.items)

    return await _reload_card(db, tenant_id, card_id)


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


async def add_block(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    data: TechCardBlockIn,
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None
    await _validate_blocks(db, tenant_id, [data])
    next_order = max((b.sort_order for b in (card.blocks or [])), default=-1) + 1
    block = TechCardBlock(
        tech_card_id=card.id,
        sort_order=next_order,
        title=data.title.strip(),
        description=(data.description.strip() if data.description else None),
        duration_minutes=int(data.duration_minutes or 0),
        photo_url=data.photo_url or None,
    )
    db.add(block)
    await db.flush()
    for item in data.items:
        db.add(
            TechCardItem(
                tech_card_id=card.id,
                block_id=block.id,
                material_id=item.material_id,
                quantity=item.quantity,
                notes=item.notes,
            )
        )
    return await _reload_card(db, tenant_id, card_id)


async def update_block(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    block_id: int,
    data: TechCardBlockIn,
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None
    block = next((b for b in (card.blocks or []) if b.id == block_id), None)
    if not block:
        raise ValueError("Блок не найден")
    await _validate_blocks(db, tenant_id, [data])
    block.title = data.title.strip()
    block.description = data.description.strip() if data.description else None
    block.duration_minutes = int(data.duration_minutes or 0)
    block.photo_url = data.photo_url or None

    old_items = (
        await db.execute(select(TechCardItem).where(TechCardItem.block_id == block.id))
    ).scalars().all()
    for old in old_items:
        await db.delete(old)
    await db.flush()
    for item in data.items:
        db.add(
            TechCardItem(
                tech_card_id=card.id,
                block_id=block.id,
                material_id=item.material_id,
                quantity=item.quantity,
                notes=item.notes,
            )
        )
    return await _reload_card(db, tenant_id, card_id)


async def delete_block(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    block_id: int,
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None
    block = next((b for b in (card.blocks or []) if b.id == block_id), None)
    if not block:
        raise ValueError("Блок не найден")
    await db.delete(block)
    await db.flush()
    remaining = (
        await db.execute(
            select(TechCardBlock)
            .where(TechCardBlock.tech_card_id == card.id)
            .order_by(TechCardBlock.sort_order.asc(), TechCardBlock.id.asc())
        )
    ).scalars().all()
    for idx, row in enumerate(remaining):
        row.sort_order = idx
    return await _reload_card(db, tenant_id, card_id)


async def reorder_blocks(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    block_ids: list[int],
) -> TechCard | None:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return None
    existing = {b.id: b for b in (card.blocks or [])}
    if not block_ids or set(block_ids) != set(existing.keys()):
        raise ValueError("Список блоков не совпадает с техкартой")
    for idx, bid in enumerate(block_ids):
        existing[bid].sort_order = idx
    return await _reload_card(db, tenant_id, card_id)
