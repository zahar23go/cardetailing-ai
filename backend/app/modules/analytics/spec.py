"""Когорты, treemap услуг, sparkline KPI, загрузка мастеров и боксов."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, Box, User, WorkingHours
from app.modules.analytics.schemas import (
    AnalyticsSpecResponse,
    CohortCell,
    CohortRow,
    LoadRow,
    SparklinePoint,
    TreemapNode,
)

_SKIP = {"cancelled", "no_show"}


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _minutes(start: datetime, end: datetime) -> int:
    delta = _utc(end) - _utc(start)
    return max(0, int(delta.total_seconds() // 60))


def _hhmm_to_min(value: str) -> int:
    parts = (value or "09:00").split(":")
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 9 * 60


async def sparkline_series(
    db: AsyncSession,
    tenant_id: UUID,
    days: int = 14,
) -> tuple[list[SparklinePoint], list[SparklinePoint], list[SparklinePoint]]:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    result = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= start,
        )
    )
    appts = result.scalars().all()
    by_day: dict[str, dict[str, float]] = defaultdict(lambda: {"rev": 0.0, "n": 0, "done": 0})
    for a in appts:
        key = _utc(a.start_time).date().isoformat()
        by_day[key]["n"] += 1
        if a.status == "completed":
            by_day[key]["done"] += 1
            by_day[key]["rev"] += float(a.total_price or 0)
    revenue: list[SparklinePoint] = []
    visits: list[SparklinePoint] = []
    done: list[SparklinePoint] = []
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        row = by_day[d]
        revenue.append(SparklinePoint(date=d, value=round(row["rev"], 2)))
        visits.append(SparklinePoint(date=d, value=row["n"]))
        done.append(SparklinePoint(date=d, value=row["done"]))
    return revenue, visits, done


async def build_spec(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    load_days: int = 7,
    cohort_months: int = 6,
) -> AnalyticsSpecResponse:
    now = datetime.now(timezone.utc)
    load_start = now - timedelta(days=load_days)
    cohort_start = (now.replace(day=1) - timedelta(days=cohort_months * 31)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    appts_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.master), selectinload(Appointment.box))
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= cohort_start,
        )
    )
    appts = appts_result.scalars().all()
    completed = [a for a in appts if a.status == "completed"]

    first_month: dict[int, str] = {}
    by_client_month: dict[int, set[str]] = defaultdict(set)
    for a in sorted(completed, key=lambda x: _utc(x.start_time)):
        cid = a.client_id
        ym = _utc(a.start_time).strftime("%Y-%m")
        by_client_month[cid].add(ym)
        if cid not in first_month:
            first_month[cid] = ym

    months: list[str] = []
    cursor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(cohort_months):
        months.append(cursor.strftime("%Y-%m"))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    months.reverse()

    grouped: dict[str, list[int]] = defaultdict(list)
    for cid, ym in first_month.items():
        if ym in months:
            grouped[ym].append(cid)

    def _shift(ym: str, offset: int) -> str:
        y, m = int(ym[:4]), int(ym[5:7])
        m += offset
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return f"{y:04d}-{m:02d}"

    cohorts: list[CohortRow] = []
    for ym in months:
        ids = grouped.get(ym, [])
        size = len(ids)
        cells: list[CohortCell] = []
        for off in range(min(6, cohort_months)):
            target = _shift(ym, off)
            n = sum(1 for cid in ids if target in by_client_month[cid]) if size else 0
            rate = round(100.0 * n / size, 1) if size else 0.0
            cells.append(CohortCell(offset=off, clients=n, rate=rate))
        cohorts.append(CohortRow(cohort=ym, size=size, cells=cells))

    treemap_acc: dict[str, dict[str, float]] = defaultdict(lambda: {"value": 0.0, "count": 0})
    recent = now - timedelta(days=90)
    for a in completed:
        if _utc(a.start_time) < recent:
            continue
        name = (a.service.name if a.service else None) or f"Услуга #{a.service_id}"
        treemap_acc[name]["value"] += float(a.total_price or 0)
        treemap_acc[name]["count"] += 1
    treemap = [
        TreemapNode(name=n, value=round(d["value"], 2), count=int(d["count"]))
        for n, d in sorted(treemap_acc.items(), key=lambda kv: kv[1]["value"], reverse=True)
    ]

    load_appts = [
        a for a in appts
        if _utc(a.start_time) >= load_start and a.status not in _SKIP
    ]

    masters_result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.role == "master")
    )
    masters = masters_result.scalars().all()
    hours_result = await db.execute(
        select(WorkingHours).where(WorkingHours.tenant_id == tenant_id)
    )
    hours_by_master: dict[int, list[WorkingHours]] = defaultdict(list)
    for row in hours_result.scalars().all():
        hours_by_master[row.master_id].append(row)

    def _capacity_master(master_id: int) -> int:
        total = 0
        for i in range(load_days):
            day = (now - timedelta(days=i)).weekday()
            rows = [h for h in hours_by_master.get(master_id, []) if h.day_of_week == day]
            if not rows:
                if day < 5:
                    total += 9 * 60
                continue
            for h in rows:
                if not h.is_working_day:
                    continue
                total += max(0, _hhmm_to_min(h.end_time) - _hhmm_to_min(h.start_time))
        return total or (9 * 60 * min(5, load_days))

    master_busy: dict[int, list[Appointment]] = defaultdict(list)
    for a in load_appts:
        if a.master_id:
            master_busy[a.master_id].append(a)

    master_rows: list[LoadRow] = []
    for m in masters:
        items = master_busy.get(m.id, [])
        busy = sum(_minutes(a.start_time, a.end_time) for a in items)
        cap = _capacity_master(m.id)
        pct = round(100.0 * busy / cap, 1) if cap else 0.0
        master_rows.append(
            LoadRow(
                id=m.id,
                name=m.full_name,
                busy_minutes=busy,
                capacity_minutes=cap,
                occupancy_pct=min(pct, 200.0),
                appointments=len(items),
            )
        )
    master_rows.sort(key=lambda r: r.occupancy_pct, reverse=True)

    boxes_result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id, Box.is_active == True)  # noqa: E712
    )
    boxes = boxes_result.scalars().all()
    box_busy: dict[int, list[Appointment]] = defaultdict(list)
    for a in load_appts:
        if a.box_id:
            box_busy[a.box_id].append(a)
    salon_day = 9 * 60
    box_cap = salon_day * load_days
    box_rows: list[LoadRow] = []
    for b in boxes:
        items = box_busy.get(b.id, [])
        busy = sum(_minutes(a.start_time, a.end_time) for a in items)
        pct = round(100.0 * busy / box_cap, 1) if box_cap else 0.0
        box_rows.append(
            LoadRow(
                id=b.id,
                name=b.name,
                busy_minutes=busy,
                capacity_minutes=box_cap,
                occupancy_pct=min(pct, 200.0),
                appointments=len(items),
            )
        )
    box_rows.sort(key=lambda r: r.occupancy_pct, reverse=True)

    return AnalyticsSpecResponse(
        cohorts=cohorts,
        treemap=treemap,
        masters=master_rows,
        boxes=box_rows,
        period_days=load_days,
    )
