"""
CRUD склада (Materials) — модуль «Технология».

HTTP-эндпоинты подключаются отдельно; здесь только работа с БД.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Material, MaterialMovement
from app.schemas import MaterialCreate, MaterialOut, MaterialUpdate

MATERIAL_CATEGORY_LABELS: dict[str, str] = {
    "chemistry": "Химия",
    "consumables": "Расходники",
    "inventory": "Инвентарь",
    "workwear": "Спецодежда",
    "other": "Прочее",
}

MATERIAL_UNIT_LABELS: dict[str, str] = {
    "pcs": "шт",
    "ml": "мл",
    "l": "л",
    "g": "г",
    "kg": "кг",
    "m": "м",
    "pack": "упак.",
}


def material_to_out(material: Material) -> MaterialOut:
    """ORM → схема ответа с вычисляемыми полями."""
    qty = float(material.quantity or 0)
    min_qty = float(material.min_quantity or 0)
    price = float(material.purchase_price or 0)
    return MaterialOut(
        id=material.id,
        name=material.name,
        sku=material.sku,
        category=material.category or "other",
        unit=material.unit or "pcs",
        quantity=qty,
        min_quantity=min_qty,
        purchase_price=price,
        supplier=material.supplier,
        notes=material.notes,
        is_active=bool(material.is_active),
        is_low_stock=qty <= min_qty,
        stock_value=round(qty * price, 2),
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


async def list_materials(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    category: str | None = None,
    is_active: bool | None = None,
    low_stock_only: bool = False,
    search: str | None = None,
) -> tuple[list[Material], int]:
    """Список материалов тенанта с фильтрами и пагинацией."""
    filters = [Material.tenant_id == tenant_id]
    if category:
        filters.append(Material.category == category)
    if is_active is not None:
        filters.append(Material.is_active == is_active)
    if low_stock_only:
        filters.append(Material.quantity <= Material.min_quantity)
    if search:
        q = f"%{search.strip()}%"
        filters.append(
            or_(
                Material.name.ilike(q),
                Material.sku.ilike(q),
                Material.supplier.ilike(q),
            )
        )

    count_result = await db.execute(
        select(func.count(Material.id)).where(*filters)
    )
    total = int(count_result.scalar() or 0)

    result = await db.execute(
        select(Material)
        .where(*filters)
        .order_by(Material.name.asc())
        .offset(skip)
        .limit(limit)
    )
    items = list(result.scalars().all())
    return items, total


async def get_material(
    db: AsyncSession,
    tenant_id: UUID,
    material_id: int,
) -> Material | None:
    """Получить материал по id внутри тенанта."""
    result = await db.execute(
        select(Material).where(
            Material.id == material_id,
            Material.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


def _movement_type_for_delta(delta: float, *, initial: bool = False) -> str:
    if initial:
        return "initial"
    if delta > 0:
        return "in"
    if delta < 0:
        return "out"
    return "adjust"


async def _log_movement(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    material_id: int,
    delta: float,
    quantity_before: float,
    quantity_after: float,
    movement_type: str | None = None,
    reason: str | None = None,
    created_by_id: int | None = None,
    appointment_id: int | None = None,
) -> None:
    db.add(
        MaterialMovement(
            tenant_id=tenant_id,
            material_id=material_id,
            movement_type=movement_type or _movement_type_for_delta(delta),
            delta=delta,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            created_by_id=created_by_id,
            appointment_id=appointment_id,
        )
    )


async def create_material(
    db: AsyncSession,
    tenant_id: UUID,
    data: MaterialCreate,
    *,
    created_by_id: int | None = None,
) -> Material:
    """Создать позицию склада."""
    qty = float(data.quantity or 0)
    material = Material(
        tenant_id=tenant_id,
        name=data.name.strip(),
        sku=(data.sku.strip() if data.sku else None),
        category=data.category or "other",
        unit=data.unit or "pcs",
        quantity=qty,
        min_quantity=data.min_quantity,
        purchase_price=data.purchase_price,
        supplier=(data.supplier.strip() if data.supplier else None),
        notes=data.notes,
        is_active=data.is_active,
    )
    db.add(material)
    await db.flush()
    if qty > 0:
        await _log_movement(
            db,
            tenant_id=tenant_id,
            material_id=material.id,
            delta=qty,
            quantity_before=0,
            quantity_after=qty,
            movement_type="initial",
            reason="Начальный остаток",
            created_by_id=created_by_id,
        )
    await db.commit()
    await db.refresh(material)
    return material


async def update_material(
    db: AsyncSession,
    tenant_id: UUID,
    material_id: int,
    data: MaterialUpdate,
    *,
    created_by_id: int | None = None,
) -> Material | None:
    """Обновить позицию склада. None если не найдена."""
    material = await get_material(db, tenant_id, material_id)
    if not material:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key in ("name", "sku", "supplier"):
        if key in update_data and isinstance(update_data[key], str):
            update_data[key] = update_data[key].strip() or None if key != "name" else update_data[key].strip()

    old_qty = float(material.quantity or 0)
    new_qty = update_data.pop("quantity", None)

    for key, value in update_data.items():
        setattr(material, key, value)

    if new_qty is not None:
        new_qty_f = float(new_qty)
        delta = new_qty_f - old_qty
        material.quantity = new_qty_f
        if abs(delta) > 1e-9:
            await _log_movement(
                db,
                tenant_id=tenant_id,
                material_id=material.id,
                delta=delta,
                quantity_before=old_qty,
                quantity_after=new_qty_f,
                movement_type="adjust",
                reason="Корректировка остатка",
                created_by_id=created_by_id,
            )

    await db.commit()
    await db.refresh(material)
    return material


async def delete_material(
    db: AsyncSession,
    tenant_id: UUID,
    material_id: int,
) -> bool:
    """Удалить позицию склада. False если не найдена."""
    material = await get_material(db, tenant_id, material_id)
    if not material:
        return False
    await db.delete(material)
    await db.commit()
    return True


async def adjust_quantity(
    db: AsyncSession,
    tenant_id: UUID,
    material_id: int,
    delta: float,
    *,
    reason: str | None = None,
    created_by_id: int | None = None,
) -> Material | None:
    """
    Изменить остаток на delta (приход +, расход −).
    Остаток не уходит ниже 0. Пишет запись в историю движений.
    """
    material = await get_material(db, tenant_id, material_id)
    if not material:
        return None
    before = float(material.quantity or 0)
    requested = before + float(delta)
    after = max(0.0, requested)
    applied = after - before
    material.quantity = after
    if abs(applied) > 1e-9:
        await _log_movement(
            db,
            tenant_id=tenant_id,
            material_id=material.id,
            delta=applied,
            quantity_before=before,
            quantity_after=after,
            reason=reason or ("Приход" if applied > 0 else "Расход"),
            created_by_id=created_by_id,
        )
    await db.commit()
    await db.refresh(material)
    return material


async def apply_stock_delta(
    db: AsyncSession,
    tenant_id: UUID,
    material_id: int,
    delta: float,
    *,
    reason: str | None = None,
    created_by_id: int | None = None,
    appointment_id: int | None = None,
) -> tuple[Material | None, float]:
    """Как adjust_quantity, но без commit. Возвращает (материал, фактически применённый delta)."""
    material = await get_material(db, tenant_id, material_id)
    if not material:
        return None, 0.0
    before = float(material.quantity or 0)
    requested = before + float(delta)
    after = max(0.0, requested)
    applied = after - before
    material.quantity = after
    if abs(applied) > 1e-9:
        await _log_movement(
            db,
            tenant_id=tenant_id,
            material_id=material.id,
            delta=applied,
            quantity_before=before,
            quantity_after=after,
            reason=reason or ("Приход" if applied > 0 else "Расход"),
            created_by_id=created_by_id,
            appointment_id=appointment_id,
        )
    await db.flush()
    return material, applied


def list_category_items() -> list[dict[str, str]]:
    """Справочник категорий для UI."""
    return [{"key": k, "label": v} for k, v in MATERIAL_CATEGORY_LABELS.items()]
