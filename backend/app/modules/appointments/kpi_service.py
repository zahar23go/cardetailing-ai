"""Личные KPI мастера: выручка, повтор, техкарта, перерасход, оценка смены."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, AppointmentInvoice
from app.modules.appointments.close_service import snapshot_revenue
from app.modules.appointments.schemas import MasterKpiOut, MasterKpiSparkPoint

SCORE_HINT = "техкарта · расход · повтор"


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_shift_score(
    *,
    completed: int,
    compliance_pct: float,
    overspend_ratio: float,
    repeat_rate: float,
    no_show_rate: float,
) -> float:
    """Оценка 0–5 по доступным сигналам. Отзывов в системе нет."""
    if completed <= 0:
        return 0.0
    compliance = max(0.0, min(compliance_pct / 100.0, 1.0))
    material = 1.0 - max(0.0, min(overspend_ratio, 1.0))
    repeat = max(0.0, min(repeat_rate, 1.0))
    show = 1.0 - max(0.0, min(no_show_rate, 1.0))
    raw = (45 * compliance + 30 * material + 15 * repeat + 10 * show) / 20.0
    return round(raw + 1e-9, 1)


def _overspend_ratio(extra_qty: float, norm_qty: float) -> float:
    if extra_qty <= 0:
        return 0.0
    if norm_qty <= 0:
        return 1.0
    return extra_qty / norm_qty


async def build_master_kpi(
    db: AsyncSession,
    tenant_id: UUID,
    master_id: int,
) -> MasterKpiOut:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spark_start = today_start - timedelta(days=13)

    lifetime_rows = (
        await db.execute(
            select(Appointment.client_id, func.count())
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.master_id == master_id,
                Appointment.status == "completed",
            )
            .group_by(Appointment.client_id)
        )
    ).all()
    lifetime_counts = {int(cid): int(n) for cid, n in lifetime_rows if cid is not None}
    repeat_ids = {cid for cid, n in lifetime_counts.items() if n >= 2}

    month_result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.invoice).selectinload(AppointmentInvoice.steps),
            selectinload(Appointment.invoice).selectinload(AppointmentInvoice.materials),
        )
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.master_id == master_id,
            Appointment.start_time >= month_start,
        )
    )
    month_appts = month_result.scalars().unique().all()

    spark_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.invoice))
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.master_id == master_id,
            Appointment.start_time >= spark_start,
        )
    )
    spark_appts = spark_result.scalars().unique().all()

    completed = [a for a in month_appts if a.status == "completed"]
    no_show_count = sum(1 for a in month_appts if a.status == "no_show")
    completed_today = sum(
        1 for a in completed if _utc(a.start_time) >= today_start
    )

    revenue = round(sum(snapshot_revenue(a) for a in completed), 2)
    completed_month = len(completed)
    avg_check = round(revenue / completed_month, 2) if completed_month else 0.0

    unique_clients = {a.client_id for a in completed}
    repeat_clients = len(unique_clients & repeat_ids)
    unique_n = len(unique_clients)
    repeat_rate_frac = (repeat_clients / unique_n) if unique_n else 0.0
    no_show_rate = (
        no_show_count / (completed_month + no_show_count)
        if (completed_month + no_show_count)
        else 0.0
    )

    steps_done = 0
    steps_total = 0
    extra_qty = 0.0
    extra_cost = 0.0
    norm_qty = 0.0
    for a in completed:
        inv = getattr(a, "invoice", None)
        if inv is None:
            continue
        for step in inv.steps or []:
            steps_total += 1
            if step.done:
                steps_done += 1
        for row in inv.materials or []:
            nq = float(row.norm_qty or 0)
            aq = float(row.actual_qty or 0)
            unit = float(row.unit_cost or 0)
            extra = max(0.0, aq - nq)
            extra_qty += extra
            extra_cost += extra * unit
            norm_qty += nq

    compliance_pct = round((steps_done / steps_total) * 100, 1) if steps_total else (100.0 if completed_month else 0.0)
    overspend_ratio = _overspend_ratio(extra_qty, norm_qty)
    overspend_pct = round(overspend_ratio * 100, 1)
    score = compute_shift_score(
        completed=completed_month,
        compliance_pct=compliance_pct,
        overspend_ratio=overspend_ratio,
        repeat_rate=repeat_rate_frac,
        no_show_rate=no_show_rate,
    )

    by_day: dict[str, float] = defaultdict(float)
    for a in spark_appts:
        if a.status != "completed":
            continue
        key = _utc(a.start_time).date().isoformat()
        by_day[key] += snapshot_revenue(a)

    sparkline: list[MasterKpiSparkPoint] = []
    for i in range(14):
        d = (spark_start + timedelta(days=i)).date().isoformat()
        sparkline.append(MasterKpiSparkPoint(date=d, value=round(by_day[d], 2)))

    return MasterKpiOut(
        period="month",
        period_start=month_start.date().isoformat(),
        revenue=revenue,
        avg_check=avg_check,
        completed_month=completed_month,
        completed_today=completed_today,
        unique_clients=unique_n,
        repeat_clients=repeat_clients,
        repeat_rate=round(repeat_rate_frac * 100, 1),
        tech_steps_done=steps_done,
        tech_steps_total=steps_total,
        tech_compliance_pct=compliance_pct,
        overspend_qty=round(extra_qty, 3),
        overspend_cost=round(extra_cost, 2),
        overspend_pct=overspend_pct,
        no_show_count=no_show_count,
        score=score,
        score_hint=SCORE_HINT,
        sparkline_revenue=sparkline,
    )
