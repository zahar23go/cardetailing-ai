"""
Аналитика модуля «Технология»:
- рекомендации по закупкам;
- аудит расхода (норма по техкартам × услуги vs факт по движениям).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Appointment,
    Material,
    MaterialMovement,
    TechCard,
    TechCardItem,
)


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "warn": 1, "plan": 2}.get(priority, 9)


async def purchase_recommendations(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
    cover_days: int = 30,
) -> list[dict]:
    """
    Рекомендации к закупке:
    target = max(min_quantity, avg_daily_consumption * cover_days)
    recommend_qty = max(0, target - current_qty)
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(days, 1))

    materials = list(
        (
            await db.execute(
                select(Material).where(
                    Material.tenant_id == tenant_id,
                    Material.is_active == True,  # noqa: E712
                )
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
    consumption: dict[int, float] = {}
    for mv in moves:
        consumption[mv.material_id] = consumption.get(mv.material_id, 0.0) + abs(float(mv.delta or 0))

    period = float(max(days, 1))
    rows: list[dict] = []
    for m in materials:
        qty = float(m.quantity or 0)
        min_q = float(m.min_quantity or 0)
        price = float(m.purchase_price or 0)
        used = consumption.get(m.id, 0.0)
        avg_daily = used / period
        target = max(min_q, avg_daily * cover_days)
        recommend = max(0.0, target - qty)
        days_left = (qty / avg_daily) if avg_daily > 0 else None

        if recommend <= 0 and qty > min_q:
            continue

        if qty <= min_q:
            priority = "critical"
            reason = "Остаток ≤ минимального запаса"
        elif days_left is not None and days_left < cover_days / 2:
            priority = "warn"
            reason = f"Хватит ≈ {round(days_left)} дн. при текущем расходе"
        elif recommend > 0:
            priority = "plan"
            reason = f"Довести запас до покрытия {cover_days} дн."
        else:
            continue

        rows.append({
            "material_id": m.id,
            "material_name": m.name,
            "sku": m.sku,
            "category": m.category,
            "unit": m.unit,
            "quantity": round(qty, 3),
            "min_quantity": round(min_q, 3),
            "avg_daily_consumption": round(avg_daily, 3),
            "days_of_stock": round(days_left, 1) if days_left is not None else None,
            "target_quantity": round(target, 3),
            "recommend_qty": round(recommend, 3),
            "purchase_price": price,
            "estimate_cost": round(recommend * price, 2),
            "supplier": m.supplier,
            "priority": priority,
            "reason": reason,
        })

    rows.sort(key=lambda r: (_priority_rank(r["priority"]), -r["estimate_cost"]))
    return rows


async def consumption_audit(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
) -> list[dict]:
    """
    Норма = сумма (qty из техкарты × число completed-услуг).
    Факт = сумма |delta| по расходным движениям за период.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(days, 1))

    cards = list(
        (
            await db.execute(
                select(TechCard)
                .options(
                    selectinload(TechCard.service),
                    selectinload(TechCard.items).selectinload(TechCardItem.material),
                )
                .where(
                    TechCard.tenant_id == tenant_id,
                    TechCard.is_active == True,  # noqa: E712
                )
            )
        ).scalars().all()
    )

    service_ids = [c.service_id for c in cards]
    service_counts: dict[int, int] = {sid: 0 for sid in service_ids}
    if service_ids:
        rows = (
            await db.execute(
                select(Appointment.service_id, func.count(Appointment.id))
                .where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.status == "completed",
                    Appointment.service_id.in_(service_ids),
                    Appointment.start_time >= start,
                )
                .group_by(Appointment.service_id)
            )
        ).all()
        for sid, cnt in rows:
            service_counts[int(sid)] = int(cnt or 0)

    norm: dict[int, float] = {}
    material_meta: dict[int, dict] = {}
    services_used: dict[int, list[dict]] = {}

    for card in cards:
        count = service_counts.get(card.service_id, 0)
        svc_name = card.service.name if card.service else f"#{card.service_id}"
        for item in card.items or []:
            mid = item.material_id
            qty_norm = float(item.quantity or 0) * count
            norm[mid] = norm.get(mid, 0.0) + qty_norm
            mat = item.material
            if mid not in material_meta:
                material_meta[mid] = {
                    "material_id": mid,
                    "material_name": mat.name if mat else f"#{mid}",
                    "unit": mat.unit if mat else "pcs",
                    "purchase_price": float(mat.purchase_price or 0) if mat else 0.0,
                    "sku": mat.sku if mat else None,
                    "category": mat.category if mat else "other",
                }
            services_used.setdefault(mid, []).append({
                "service_id": card.service_id,
                "service_name": svc_name,
                "completed_count": count,
                "norm_per_service": float(item.quantity or 0),
                "norm_total": round(qty_norm, 3),
            })

    fact_moves = list(
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
    fact: dict[int, float] = {}
    for mv in fact_moves:
        fact[mv.material_id] = fact.get(mv.material_id, 0.0) + abs(float(mv.delta or 0))

    # материалы с фактом, но без техкарты
    orphan_ids = [mid for mid in fact if mid not in material_meta]
    if orphan_ids:
        mats = list(
            (
                await db.execute(select(Material).where(Material.id.in_(orphan_ids)))
            ).scalars().all()
        )
        for m in mats:
            material_meta[m.id] = {
                "material_id": m.id,
                "material_name": m.name,
                "unit": m.unit,
                "purchase_price": float(m.purchase_price or 0),
                "sku": m.sku,
                "category": m.category,
            }

    all_ids = set(norm) | set(fact)
    out: list[dict] = []
    for mid in all_ids:
        meta = material_meta.get(mid)
        if not meta:
            continue
        n = round(norm.get(mid, 0.0), 3)
        f = round(fact.get(mid, 0.0), 3)
        variance = round(f - n, 3)
        if n > 0:
            variance_pct = round((f / n - 1.0) * 100, 1)
        elif f > 0:
            variance_pct = None
        else:
            variance_pct = 0.0

        if n <= 0 and f > 0:
            status = "no_norm"
            status_label = "Нет нормы"
        elif n > 0 and f <= 0:
            status = "no_fact"
            status_label = "Нет факта"
        elif n > 0 and f > n * 1.1:
            status = "over"
            status_label = "Перерасход"
        elif n > 0 and f < n * 0.9:
            status = "under"
            status_label = "Недорасход"
        else:
            status = "ok"
            status_label = "В норме"

        price = float(meta["purchase_price"] or 0)
        out.append({
            **meta,
            "norm_qty": n,
            "fact_qty": f,
            "variance_qty": variance,
            "variance_percent": variance_pct,
            "norm_cost": round(n * price, 2),
            "fact_cost": round(f * price, 2),
            "variance_cost": round(variance * price, 2),
            "status": status,
            "status_label": status_label,
            "services": services_used.get(mid, []),
        })

    status_order = {"over": 0, "no_norm": 1, "under": 2, "no_fact": 3, "ok": 4}
    out.sort(key=lambda r: (status_order.get(r["status"], 9), -abs(r["variance_cost"])))
    return out


async def tech_analytics_summary(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
    cover_days: int = 30,
) -> dict:
    purchases = await purchase_recommendations(
        db, tenant_id, days=days, cover_days=cover_days
    )
    audit = await consumption_audit(db, tenant_id, days=days)

    purchase_cost = round(sum(r["estimate_cost"] for r in purchases), 2)
    critical = sum(1 for r in purchases if r["priority"] == "critical")
    over = sum(1 for r in audit if r["status"] == "over")
    under = sum(1 for r in audit if r["status"] == "under")
    variance_cost = round(sum(r["variance_cost"] for r in audit), 2)

    return {
        "period_days": days,
        "cover_days": cover_days,
        "purchase_items": len(purchases),
        "purchase_estimate_cost": purchase_cost,
        "purchase_critical": critical,
        "audit_items": len(audit),
        "audit_overspend": over,
        "audit_underspend": under,
        "audit_variance_cost": variance_cost,
    }
