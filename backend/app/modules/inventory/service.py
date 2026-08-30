"""
Учёт склада (Inventory): история движений, график остатка, ABC, критические позиции.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Material, MaterialMovement


MOVEMENT_TYPE_LABELS = {
    "in": "Приход",
    "out": "Расход",
    "adjust": "Корректировка",
    "initial": "Начальный остаток",
    "revision": "Ревизия",
}


def movement_to_out(m: MaterialMovement) -> dict:
    mat = m.material
    return {
        "id": m.id,
        "material_id": m.material_id,
        "material_name": mat.name if mat else f"#{m.material_id}",
        "material_unit": mat.unit if mat else "pcs",
        "movement_type": m.movement_type,
        "movement_type_label": MOVEMENT_TYPE_LABELS.get(m.movement_type, m.movement_type),
        "delta": float(m.delta or 0),
        "quantity_before": float(m.quantity_before or 0),
        "quantity_after": float(m.quantity_after or 0),
        "reason": m.reason,
        "created_at": m.created_at,
    }


async def list_movements(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    material_id: int | None = None,
    movement_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[MaterialMovement], int]:
    filters = [MaterialMovement.tenant_id == tenant_id]
    if material_id is not None:
        filters.append(MaterialMovement.material_id == material_id)
    if movement_type:
        filters.append(MaterialMovement.movement_type == movement_type)
    if date_from:
        filters.append(MaterialMovement.created_at >= date_from)
    if date_to:
        filters.append(MaterialMovement.created_at <= date_to)

    total = int(
        (await db.execute(select(func.count(MaterialMovement.id)).where(*filters))).scalar() or 0
    )
    result = await db.execute(
        select(MaterialMovement)
        .options(selectinload(MaterialMovement.material))
        .where(*filters)
        .order_by(MaterialMovement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def stock_history(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    material_id: int | None = None,
    days: int = 30,
) -> list[dict]:
    """
    Дневной график остатка.
    Если material_id задан — остаток по позиции, иначе суммарный stock_value (qty×price).
    """
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=max(days - 1, 0))).replace(hour=0, minute=0, second=0, microsecond=0)

    mats_q = select(Material).where(Material.tenant_id == tenant_id, Material.is_active == True)
    if material_id is not None:
        mats_q = mats_q.where(Material.id == material_id)
    materials = list((await db.execute(mats_q)).scalars().all())
    if not materials:
        return []

    mat_ids = [m.id for m in materials]
    price_map = {m.id: float(m.purchase_price or 0) for m in materials}
    current = {m.id: float(m.quantity or 0) for m in materials}

    moves = list(
        (
            await db.execute(
                select(MaterialMovement)
                .where(
                    MaterialMovement.tenant_id == tenant_id,
                    MaterialMovement.material_id.in_(mat_ids),
                    MaterialMovement.created_at >= start,
                )
                .order_by(MaterialMovement.created_at.asc())
            )
        ).scalars().all()
    )

    # Откатываем текущие остатки к началу периода
    qty = dict(current)
    for mv in reversed(moves):
        qty[mv.material_id] = float(mv.quantity_before or 0)

    # Группируем движения по дням
    by_day: dict[str, list[MaterialMovement]] = {}
    for mv in moves:
        if not mv.created_at:
            continue
        key = mv.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(key, []).append(mv)

    points: list[dict] = []
    cursor = start
    while cursor.date() <= now.date():
        key = cursor.strftime("%Y-%m-%d")
        for mv in by_day.get(key, []):
            qty[mv.material_id] = float(mv.quantity_after or 0)

        if material_id is not None:
            value = round(qty.get(material_id, 0.0), 3)
            points.append({"date": key, "quantity": value, "value": round(value * price_map.get(material_id, 0), 2)})
        else:
            total_qty = round(sum(qty.values()), 3)
            total_val = round(sum(q * price_map.get(mid, 0) for mid, q in qty.items()), 2)
            points.append({"date": key, "quantity": total_qty, "value": total_val})

        cursor += timedelta(days=1)

    return points


async def abc_analysis(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 90,
) -> list[dict]:
    """
    ABC по стоимости расхода за период.
    A ≈ 80% суммарного расхода, B ≈ 15%, C ≈ 5%.
    Если движений нет — fallback на стоимость текущего остатка.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    materials = list(
        (
            await db.execute(
                select(Material).where(Material.tenant_id == tenant_id, Material.is_active == True)
            )
        ).scalars().all()
    )
    if not materials:
        return []

    moves = list(
        (
            await db.execute(
                select(MaterialMovement).where(
                    MaterialMovement.tenant_id == tenant_id,
                    MaterialMovement.created_at >= start,
                    MaterialMovement.delta < 0,
                )
            )
        ).scalars().all()
    )

    consumption: dict[int, float] = {m.id: 0.0 for m in materials}
    for mv in moves:
        consumption[mv.material_id] = consumption.get(mv.material_id, 0.0) + abs(float(mv.delta or 0))

    rows = []
    for m in materials:
        price = float(m.purchase_price or 0)
        qty_used = consumption.get(m.id, 0.0)
        stock_val = float(m.quantity or 0) * price
        spend = qty_used * price
        metric = spend if spend > 0 else stock_val
        rows.append({
            "material_id": m.id,
            "material_name": m.name,
            "category": m.category,
            "unit": m.unit,
            "consumption_qty": round(qty_used, 3),
            "consumption_value": round(spend, 2),
            "stock_value": round(stock_val, 2),
            "metric_value": round(metric, 2),
            "quantity": float(m.quantity or 0),
            "min_quantity": float(m.min_quantity or 0),
            "is_low_stock": float(m.quantity or 0) <= float(m.min_quantity or 0),
        })

    rows.sort(key=lambda r: r["metric_value"], reverse=True)
    total = sum(r["metric_value"] for r in rows) or 1.0
    cumulative = 0.0
    for r in rows:
        share = r["metric_value"] / total * 100
        cumulative += share
        r["share_percent"] = round(share, 1)
        r["cumulative_percent"] = round(cumulative, 1)
        if cumulative <= 80:
            r["abc_class"] = "A"
        elif cumulative <= 95:
            r["abc_class"] = "B"
        else:
            r["abc_class"] = "C"
    return rows


async def critical_positions(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[dict]:
    """Позиции с остатком ≤ мин. запаса."""
    materials = list(
        (
            await db.execute(
                select(Material)
                .where(
                    Material.tenant_id == tenant_id,
                    Material.is_active == True,
                    Material.quantity <= Material.min_quantity,
                )
                .order_by(Material.quantity.asc())
            )
        ).scalars().all()
    )
    out = []
    for m in materials:
        qty = float(m.quantity or 0)
        mn = float(m.min_quantity or 0)
        deficit = max(0.0, mn - qty)
        out.append({
            "material_id": m.id,
            "material_name": m.name,
            "sku": m.sku,
            "category": m.category,
            "unit": m.unit,
            "quantity": qty,
            "min_quantity": mn,
            "deficit": round(deficit, 3),
            "purchase_price": float(m.purchase_price or 0),
            "restock_cost": round(deficit * float(m.purchase_price or 0), 2),
            "supplier": m.supplier,
        })
    return out


async def inventory_summary(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
) -> dict:
    materials = list(
        (
            await db.execute(
                select(Material).where(Material.tenant_id == tenant_id, Material.is_active == True)
            )
        ).scalars().all()
    )
    stock_value = round(sum(float(m.quantity or 0) * float(m.purchase_price or 0) for m in materials), 2)
    critical = await critical_positions(db, tenant_id)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    move_count = int(
        (
            await db.execute(
                select(func.count(MaterialMovement.id)).where(
                    MaterialMovement.tenant_id == tenant_id,
                    MaterialMovement.created_at >= start,
                )
            )
        ).scalar()
        or 0
    )
    return {
        "materials_count": len(materials),
        "stock_value": stock_value,
        "critical_count": len(critical),
        "movements_period": move_count,
        "period_days": days,
    }
