"""
Аналитика модуля «Технология»:
- рекомендации по закупкам;
- аудит расхода (норма по техкартам × услуги vs факт по движениям);
- аномалии расхода;
- журнал AuditLog.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Appointment,
    AuditLog,
    Material,
    MaterialMovement,
    TechCard,
    TechCardItem,
)


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "warn": 1, "plan": 2}.get(priority, 9)


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "warn": 1, "info": 2}.get(severity, 9)


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


async def detect_anomalies(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
) -> list[dict]:
    """
    Аномалии склада:
    - spike: расход во 2-й половине периода ≥ 2× 1-й половины;
    - overspend: факт > нормы на ≥25%;
    - burst: одно списание ≥ 40% всего расхода за период;
    - ghost: расход есть, а техкарты/нормы нет.
    """
    now = datetime.now(timezone.utc)
    period = max(days, 2)
    start = now - timedelta(days=period)
    mid = now - timedelta(days=period // 2)

    materials = {
        m.id: m
        for m in (
            await db.execute(
                select(Material).where(
                    Material.tenant_id == tenant_id,
                    Material.is_active == True,  # noqa: E712
                )
            )
        ).scalars().all()
    }
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

    first_half: dict[int, float] = {}
    second_half: dict[int, float] = {}
    totals: dict[int, float] = {}
    max_burst: dict[int, float] = {}

    for mv in moves:
        qty = abs(float(mv.delta or 0))
        mid_id = mv.material_id
        totals[mid_id] = totals.get(mid_id, 0.0) + qty
        max_burst[mid_id] = max(max_burst.get(mid_id, 0.0), qty)
        created = mv.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and created < mid:
            first_half[mid_id] = first_half.get(mid_id, 0.0) + qty
        else:
            second_half[mid_id] = second_half.get(mid_id, 0.0) + qty

    audit_rows = await consumption_audit(db, tenant_id, days=days)
    audit_by_mat = {r["material_id"]: r for r in audit_rows}

    anomalies: list[dict] = []

    for mid, total in totals.items():
        mat = materials.get(mid)
        if not mat or total <= 0:
            continue
        name = mat.name
        unit = mat.unit
        price = float(mat.purchase_price or 0)

        fh = first_half.get(mid, 0.0)
        sh = second_half.get(mid, 0.0)
        if fh > 0 and sh >= fh * 2:
            ratio = round(sh / fh, 2)
            anomalies.append({
                "code": "spike",
                "severity": "warn" if ratio < 3 else "critical",
                "material_id": mid,
                "material_name": name,
                "unit": unit,
                "title": f"Скачок расхода: {name}",
                "message": (
                    f"Во 2-й половине периода списано {round(sh, 3)} {unit} "
                    f"против {round(fh, 3)} {unit} в 1-й (×{ratio})."
                ),
                "metric_value": ratio,
                "cost_impact": round((sh - fh) * price, 2),
                "fingerprint": f"anomaly:spike:{mid}",
            })

        burst = max_burst.get(mid, 0.0)
        if total > 0 and burst >= total * 0.4 and burst > 0:
            share = round(burst / total * 100, 1)
            anomalies.append({
                "code": "burst",
                "severity": "warn" if share < 60 else "critical",
                "material_id": mid,
                "material_name": name,
                "unit": unit,
                "title": f"Крупное разовое списание: {name}",
                "message": (
                    f"Одно списание {round(burst, 3)} {unit} = {share}% "
                    f"расхода за период ({round(total, 3)} {unit})."
                ),
                "metric_value": share,
                "cost_impact": round(burst * price, 2),
                "fingerprint": f"anomaly:burst:{mid}",
            })

        ar = audit_by_mat.get(mid)
        if ar and ar["status"] == "over" and ar.get("variance_percent") is not None:
            vp = float(ar["variance_percent"])
            if vp >= 25:
                anomalies.append({
                    "code": "overspend",
                    "severity": "critical" if vp >= 50 else "warn",
                    "material_id": mid,
                    "material_name": name,
                    "unit": unit,
                    "title": f"Перерасход vs норма: {name}",
                    "message": (
                        f"Факт {ar['fact_qty']} {unit} при норме {ar['norm_qty']} {unit} "
                        f"(+{vp}%)."
                    ),
                    "metric_value": vp,
                    "cost_impact": float(ar.get("variance_cost") or 0),
                    "fingerprint": f"anomaly:overspend:{mid}",
                })
        elif ar and ar["status"] == "no_norm" and ar["fact_qty"] > 0:
            anomalies.append({
                "code": "ghost",
                "severity": "warn",
                "material_id": mid,
                "material_name": name,
                "unit": unit,
                "title": f"Расход без нормы: {name}",
                "message": (
                    f"Списано {ar['fact_qty']} {unit}, но материал не в техкартах "
                    f"или нет завершённых услуг."
                ),
                "metric_value": float(ar["fact_qty"]),
                "cost_impact": float(ar.get("fact_cost") or 0),
                "fingerprint": f"anomaly:ghost:{mid}",
            })

    anomalies.sort(key=lambda a: (_severity_rank(a["severity"]), -abs(a["cost_impact"])))
    return anomalies


def _event_from_purchase(row: dict) -> dict | None:
    if row["priority"] == "plan" and row["recommend_qty"] <= 0:
        return None
    severity = "critical" if row["priority"] == "critical" else (
        "warn" if row["priority"] == "warn" else "info"
    )
    return {
        "kind": "recommendation",
        "severity": severity,
        "material_id": row["material_id"],
        "title": f"Закупка: {row['material_name']}",
        "message": (
            f"{row['reason']}. Купить {row['recommend_qty']} {row['unit']} "
            f"(~{row['estimate_cost']} ₽)."
        ),
        "payload": {
            "recommend_qty": row["recommend_qty"],
            "estimate_cost": row["estimate_cost"],
            "priority": row["priority"],
        },
        "fingerprint": f"recommendation:{row['priority']}:{row['material_id']}",
    }


def _event_from_audit(row: dict) -> dict | None:
    if row["status"] not in ("over", "under", "no_norm"):
        return None
    severity = "critical" if row["status"] == "over" else "warn"
    return {
        "kind": "audit",
        "severity": severity,
        "material_id": row["material_id"],
        "title": f"{row['status_label']}: {row['material_name']}",
        "message": (
            f"Норма {row['norm_qty']} {row['unit']}, факт {row['fact_qty']} {row['unit']}, "
            f"Δ {row['variance_qty']} ({row.get('variance_percent')}%)."
        ),
        "payload": {
            "status": row["status"],
            "norm_qty": row["norm_qty"],
            "fact_qty": row["fact_qty"],
            "variance_cost": row["variance_cost"],
        },
        "fingerprint": f"audit:{row['status']}:{row['material_id']}",
    }


def _event_from_anomaly(row: dict) -> dict:
    return {
        "kind": "anomaly",
        "severity": row["severity"],
        "material_id": row["material_id"],
        "title": row["title"],
        "message": row["message"],
        "payload": {
            "code": row["code"],
            "metric_value": row["metric_value"],
            "cost_impact": row["cost_impact"],
        },
        "fingerprint": row["fingerprint"],
    }


async def sync_audit_logs(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    days: int = 30,
    cover_days: int = 30,
) -> dict:
    """Пересчитать рекомендации/аудит/аномалии и синхронизировать open-записи AuditLog."""
    purchases = await purchase_recommendations(
        db, tenant_id, days=days, cover_days=cover_days
    )
    audit = await consumption_audit(db, tenant_id, days=days)
    anomalies = await detect_anomalies(db, tenant_id, days=days)

    events: list[dict] = []
    for p in purchases:
        ev = _event_from_purchase(p)
        if ev:
            events.append(ev)
    for a in audit:
        ev = _event_from_audit(a)
        if ev:
            events.append(ev)
    for an in anomalies:
        events.append(_event_from_anomaly(an))

    wanted = {e["fingerprint"] for e in events}

    existing = list(
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.status == "open",
                )
            )
        ).scalars().all()
    )
    by_fp = {e.fingerprint: e for e in existing}

    created = 0
    updated = 0
    resolved = 0
    now = datetime.now(timezone.utc)

    for ev in events:
        row = by_fp.get(ev["fingerprint"])
        if row:
            row.severity = ev["severity"]
            row.title = ev["title"]
            row.message = ev["message"]
            row.payload = ev["payload"]
            row.material_id = ev["material_id"]
            updated += 1
        else:
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    kind=ev["kind"],
                    severity=ev["severity"],
                    material_id=ev["material_id"],
                    title=ev["title"],
                    message=ev["message"],
                    payload=ev["payload"],
                    status="open",
                    fingerprint=ev["fingerprint"],
                )
            )
            created += 1

    for row in existing:
        if row.fingerprint not in wanted:
            row.status = "resolved"
            row.resolved_at = now
            resolved += 1

    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "resolved": resolved,
        "open_total": len(events),
        "recommendations": len(purchases),
        "audit_rows": len(audit),
        "anomalies": len(anomalies),
    }


async def list_audit_logs(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    kind: str | None = None,
    status: str | None = "open",
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[AuditLog], int]:
    filters = [AuditLog.tenant_id == tenant_id]
    if kind:
        filters.append(AuditLog.kind == kind)
    if status:
        filters.append(AuditLog.status == status)

    total = int(
        (await db.execute(select(func.count(AuditLog.id)).where(*filters))).scalar() or 0
    )
    rows = list(
        (
            await db.execute(
                select(AuditLog)
                .options(selectinload(AuditLog.material))
                .where(*filters)
                .order_by(AuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()
    )
    return rows, total


def audit_log_to_out(row: AuditLog) -> dict:
    mat = row.material
    return {
        "id": row.id,
        "kind": row.kind,
        "severity": row.severity,
        "material_id": row.material_id,
        "material_name": mat.name if mat else None,
        "title": row.title,
        "message": row.message,
        "payload": row.payload or {},
        "status": row.status,
        "fingerprint": row.fingerprint,
        "created_at": row.created_at,
        "resolved_at": row.resolved_at,
    }


async def resolve_audit_log(
    db: AsyncSession,
    tenant_id: UUID,
    log_id: int,
) -> AuditLog | None:
    row = (
        await db.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.material))
            .where(
                AuditLog.id == log_id,
                AuditLog.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row, attribute_names=["status", "resolved_at"])
    return row


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
    anomalies = await detect_anomalies(db, tenant_id, days=days)

    purchase_cost = round(sum(r["estimate_cost"] for r in purchases), 2)
    critical = sum(1 for r in purchases if r["priority"] == "critical")
    over = sum(1 for r in audit if r["status"] == "over")
    under = sum(1 for r in audit if r["status"] == "under")
    variance_cost = round(sum(r["variance_cost"] for r in audit), 2)
    open_logs = int(
        (
            await db.execute(
                select(func.count(AuditLog.id)).where(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.status == "open",
                )
            )
        ).scalar()
        or 0
    )

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
        "anomaly_count": len(anomalies),
        "open_audit_logs": open_logs,
    }
