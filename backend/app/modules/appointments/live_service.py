"""Снимок боксов «прямо сейчас»: занятость, подготовка слота, ближайшая запись."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, Box

PREP_MINUTES = 15
FLOOR_STATUSES = ("pending", "confirmed", "in_progress")
STATE_LABELS = {
    "occupied": "В работе",
    "preparing": "Подготовка слота",
    "booked": "Забронирован",
    "free": "Свободен",
    "inactive": "Выключен",
}


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def visit_payload(appointment: Appointment, now: datetime) -> dict:
    start = _aware(appointment.start_time)
    end = _aware(appointment.end_time)
    elapsed = 0
    remaining = 0
    overrun = False
    if start:
        elapsed = max(0, int((now - start).total_seconds() // 60))
    if end:
        remaining = int((end - now).total_seconds() // 60)
        overrun = remaining < 0 and appointment.status == "in_progress"
    return {
        "id": appointment.id,
        "status": appointment.status,
        "service_name": appointment.service.name if appointment.service else "",
        "client_name": appointment.client.full_name if appointment.client else "",
        "master_name": appointment.master.full_name if appointment.master else None,
        "master_id": appointment.master_id,
        "start_time": start,
        "end_time": end,
        "elapsed_minutes": elapsed,
        "remaining_minutes": remaining,
        "overrun": overrun,
    }


def pick_current(appts: list[Appointment], now: datetime) -> Appointment | None:
    in_progress = [a for a in appts if a.status == "in_progress"]
    if in_progress:
        in_progress.sort(key=lambda a: _aware(a.start_time) or now, reverse=True)
        return in_progress[0]
    overlapping = []
    for a in appts:
        start, end = _aware(a.start_time), _aware(a.end_time)
        if start and end and start <= now <= end:
            overlapping.append(a)
    if overlapping:
        overlapping.sort(key=lambda a: _aware(a.start_time) or now)
        return overlapping[0]
    return None


def pick_next(appts: list[Appointment], now: datetime, current_id: int | None) -> Appointment | None:
    future = []
    for a in appts:
        if current_id is not None and a.id == current_id:
            continue
        start = _aware(a.start_time)
        if start and start > now:
            future.append(a)
    future.sort(key=lambda a: _aware(a.start_time) or now)
    return future[0] if future else None


def box_state(current: Appointment | None, nxt: Appointment | None, now: datetime, is_active: bool) -> str:
    if not is_active:
        return "inactive"
    if current and current.status == "in_progress":
        return "occupied"
    if current:
        return "preparing"
    if nxt:
        start = _aware(nxt.start_time)
        if start:
            mins = (start - now).total_seconds() / 60
            if mins <= PREP_MINUTES:
                return "preparing"
            if start.date() == now.date():
                return "booked"
    return "free"


async def build_live_floor(db: AsyncSession, tenant_id: UUID) -> dict:
    now = datetime.now(timezone.utc)
    window_from = now - timedelta(hours=12)
    window_to = now + timedelta(hours=24)

    boxes = (
        await db.execute(
            select(Box)
            .where(Box.tenant_id == tenant_id)
            .order_by(Box.sort_order, Box.name)
        )
    ).scalars().all()

    appts = (
        await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.master),
                selectinload(Appointment.service),
            )
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.box_id.is_not(None),
                Appointment.status.in_(FLOOR_STATUSES),
                or_(
                    Appointment.status == "in_progress",
                    (
                        (Appointment.start_time < window_to)
                        & (Appointment.end_time > window_from)
                    ),
                ),
            )
        )
    ).scalars().all()

    by_box: dict[int, list[Appointment]] = {}
    for a in appts:
        by_box.setdefault(int(a.box_id), []).append(a)

    items = []
    for box in boxes:
        group = by_box.get(box.id, [])
        current = pick_current(group, now)
        nxt = pick_next(group, now, current.id if current else None)
        state = box_state(current, nxt, now, bool(box.is_active))
        items.append({
            "box_id": box.id,
            "name": box.name,
            "color": box.color,
            "is_active": bool(box.is_active),
            "state": state,
            "state_label": STATE_LABELS[state],
            "current": visit_payload(current, now) if current else None,
            "next": visit_payload(nxt, now) if nxt else None,
        })

    return {
        "server_time": now,
        "prep_minutes": PREP_MINUTES,
        "boxes": items,
    }
