"""
Notification Service — управление уведомлениями в БД + отправка.
"""

from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Notification, UserNotificationSettings, User, Appointment


# =========================================================================
# Управление уведомлениями в БД
# =========================================================================

async def create_notification(
    db: AsyncSession,
    user_id: int,
    tenant_id: UUID,
    title: str,
    message: str,
    type: str = "info",
    channel: str = "in_app",
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
) -> Notification:
    """Создать уведомление."""
    notif = Notification(
        user_id=user_id,
        tenant_id=tenant_id,
        type=type,
        channel=channel,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def get_notifications(
    db: AsyncSession,
    user_id: int,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    """Получить список уведомлений (с пагинацией)."""
    stmt = (
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
        )
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()
    return list(items), total


async def get_unread_count(db: AsyncSession, user_id: int, tenant_id: UUID) -> int:
    """Получить количество непрочитанных уведомлений."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_read == False,
        )
    )
    return result.scalar() or 0


async def mark_as_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    """Отметить уведомление как прочитанное."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount > 0


async def mark_all_as_read(db: AsyncSession, user_id: int, tenant_id: UUID) -> int:
    """Отметить все уведомления как прочитанные. Возвращает количество."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount


# =========================================================================
# Настройки уведомлений
# =========================================================================

async def get_settings(db: AsyncSession, user_id: int) -> UserNotificationSettings | None:
    result = await db.execute(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_settings(
    db: AsyncSession,
    user_id: int,
    **kwargs,
) -> UserNotificationSettings:
    """Создать или обновить настройки уведомлений."""
    existing = await get_settings(db, user_id)
    if existing:
        for key, value in kwargs.items():
            setattr(existing, key, value)
    else:
        existing = UserNotificationSettings(user_id=user_id, **kwargs)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


# =========================================================================
# Фоновые задачи (напоминания)
# =========================================================================

async def send_appointment_reminders(db: AsyncSession, hours_before: int = 24):
    """Отправить напоминания о предстоящих записях."""
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=hours_before)
    window_end = window_start + timedelta(hours=1)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service))
        .where(
            Appointment.start_time >= window_start,
            Appointment.start_time <= window_end,
            Appointment.status.in_(["pending", "confirmed"]),
        )
    )
    appts = result.scalars().all()

    sent = 0
    for appt in appts:
        if not appt.client:
            continue
        title = "Напоминание о записи"
        message = (
            f"Напоминаем, что завтра в {appt.start_time.strftime('%H:%M')} "
            f"у вас запись на «{appt.service.name if appt.service else 'услугу'}». "
            f"Ждём вас!"
        )
        await create_notification(
            db, appt.client_id, appt.tenant_id,
            title, message,
            type="appointment_reminder",
            related_entity_type="appointment",
            related_entity_id=appt.id,
        )

        # Получаем настройки для Telegram/SMS
        settings = await get_settings(db, appt.client_id)
        if settings:
            if settings.telegram_enabled and settings.telegram_chat_id:
                try:
                    from app.core.telegram_service import send_telegram_message
                    await send_telegram_message(settings.telegram_chat_id, f"📅 {title}\n\n{message}")
                except Exception:
                    pass
            if settings.sms_enabled and settings.sms_phone:
                try:
                    from app.core.sms_service import send_sms
                    await send_sms(settings.sms_phone, f"{title}: {message}")
                except Exception:
                    pass
        sent += 1
    return sent
