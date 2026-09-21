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
    """Создать уведомление (или обновить существующее, если дубликат за последние 5 минут)."""
    now = datetime.now(timezone.utc)
    # Проверить, есть ли такое уведомление за последние 5 минут
    existing = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.title == title,
            Notification.related_entity_type == related_entity_type,
            Notification.related_entity_id == related_entity_id,
            Notification.created_at > now - timedelta(minutes=5)
        )
    )
    existing_notif = existing.scalar_one_or_none()
    if existing_notif:
        existing_notif.message = message
        existing_notif.created_at = now
        await db.commit()
        await db.refresh(existing_notif)
        return existing_notif

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
            Notification.title.isnot(None),
            Notification.message.isnot(None),
            Notification.created_at.isnot(None),
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

# Верхняя граница горизонта напоминаний: схема настроек разрешает до 168 ч (неделя).
MAX_REMIND_HOURS = 168
REMINDER_TYPE = "appointment_reminder"


def _as_aware(value: datetime) -> datetime:
    """SQLite отдаёт naive datetime — считаем его UTC, чтобы сравнивать с now."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _reminder_already_sent(db: AsyncSession, appt: Appointment) -> bool:
    """Есть ли уже напоминание клиенту по этой записи."""
    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == appt.client_id,
            Notification.tenant_id == appt.tenant_id,
            Notification.type == REMINDER_TYPE,
            Notification.related_entity_id == appt.id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def send_appointment_reminders(db: AsyncSession, hours_before: int = 1) -> int:
    """Отправить напоминания о предстоящих записях.

    За сколько напоминать — из личных настроек клиента (remind_hours_before),
    иначе из hours_before. Каналы: in-app всегда, Telegram/SMS — если включены.
    Повторный вызов по той же записи напоминание не дублирует.
    """
    now = datetime.now(timezone.utc)
    lookahead = now + timedelta(hours=MAX_REMIND_HOURS)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service))
        .where(
            Appointment.start_time > now,
            Appointment.start_time <= lookahead,
            Appointment.status.in_(["pending", "confirmed"]),
        )
    )
    appts = result.scalars().all()

    sent = 0
    for appt in appts:
        if not appt.client:
            continue

        settings = await get_settings(db, appt.client_id)
        if settings and not settings.notify_appointment_reminder:
            continue
        remind_hours = settings.remind_hours_before if settings else hours_before
        start_time = _as_aware(appt.start_time)
        if now < start_time - timedelta(hours=remind_hours):
            continue
        if await _reminder_already_sent(db, appt):
            continue

        title = "Напоминание о записи"
        message = (
            f"Напоминаем, что в {start_time.strftime('%H:%M')} "
            f"у вас запись на «{appt.service.name if appt.service else 'услугу'}». "
            f"Ждём вас!"
        )
        await create_notification(
            db, appt.client_id, appt.tenant_id,
            title, message,
            type=REMINDER_TYPE,
            related_entity_type="appointment",
            related_entity_id=appt.id,
        )

        # Telegram/SMS — если клиент их включил и настроил
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
