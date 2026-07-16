"""
HistoryService — логирование изменений записей (Appointments).
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AppointmentHistory, Appointment, User


async def log_create(
    db: AsyncSession,
    appointment: Appointment,
    user_id: int,
):
    """Логирование создания записи."""
    entry = AppointmentHistory(
        appointment_id=appointment.id,
        changed_by_id=user_id,
        change_type="create",
        field_name="appointment",
        old_value=None,
        new_value=(
            f"service={appointment.service_id}, "
            f"car={appointment.car_id}, "
            f"start={appointment.start_time.isoformat() if appointment.start_time else '?'}, "
            f"price={appointment.total_price}"
        ),
    )
    db.add(entry)
    await db.commit()


async def log_update(
    db: AsyncSession,
    appointment_id: int,
    old_data: dict,
    new_data: dict,
    user_id: int,
):
    """Логирование обновления полей (сравнивает old и new)."""
    changes = []
    tracked_fields = {"status", "start_time", "end_time", "total_price", "master_id", "car_id", "service_id", "client_notes", "master_brief"}

    for field in tracked_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        if old_val != new_val:
            changes.append((field, str(old_val or ""), str(new_val or "")))

    if not changes:
        return

    for field, old_v, new_v in changes:
        entry = AppointmentHistory(
            appointment_id=appointment_id,
            changed_by_id=user_id,
            change_type="update",
            field_name=field,
            old_value=old_v,
            new_value=new_v,
        )
        db.add(entry)

    await db.commit()


async def log_cancel(
    db: AsyncSession,
    appointment: Appointment,
    user_id: int,
):
    """Логирование отмены записи."""
    entry = AppointmentHistory(
        appointment_id=appointment.id,
        changed_by_id=user_id,
        change_type="cancel",
        field_name="status",
        old_value=appointment.status or "pending",
        new_value="cancelled",
    )
    db.add(entry)
    await db.commit()


async def log_move(
    db: AsyncSession,
    appointment_id: int,
    old_start: str,
    new_start: str,
    user_id: int,
):
    """Логирование переноса записи."""
    entry = AppointmentHistory(
        appointment_id=appointment_id,
        changed_by_id=user_id,
        change_type="move",
        field_name="start_time",
        old_value=old_start,
        new_value=new_start,
    )
    db.add(entry)
    await db.commit()


async def log_status_change(
    db: AsyncSession,
    appointment_id: int,
    old_status: str,
    new_status: str,
    user_id: int,
):
    """Логирование смены статуса."""
    entry = AppointmentHistory(
        appointment_id=appointment_id,
        changed_by_id=user_id,
        change_type="status_change",
        field_name="status",
        old_value=old_status,
        new_value=new_status,
    )
    db.add(entry)
    await db.commit()


async def get_history(
    db: AsyncSession,
    appointment_id: int,
    skip: int = 0,
    limit: int = 50,
    change_type: str | None = None,
) -> tuple[list[AppointmentHistory], int]:
    """Получить историю изменений с пагинацией."""
    stmt = (
        select(AppointmentHistory)
        .options(selectinload(AppointmentHistory.changed_by))
        .where(AppointmentHistory.appointment_id == appointment_id)
        .order_by(AppointmentHistory.created_at.desc())
    )
    if change_type:
        stmt = stmt.where(AppointmentHistory.change_type == change_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()
    return list(items), total
