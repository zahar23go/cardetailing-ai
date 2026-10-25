"""152-ФЗ: версия согласия и право на забвение (обезличивание клиента).

Удалять пользователя нельзя: записи и чеки ссылаются на него каскадом и
составляют финансовую историю салона. Поэтому персональные данные
обезличиваются, а агрегированные записи остаются.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.image_service import delete_file_local
from app.models import (
    AiChatLog,
    Appointment,
    Car,
    ClientDiscount,
    DetailerInspection,
    DiscountRule,
    LoyaltyPoints,
    Notification,
    Photo,
    User,
    UserNotificationSettings,
)

CONSENT_VERSION = "2026-10-25"
PRIVACY_POLICY_VERSION = CONSENT_VERSION
ANONYMIZED_NAME = "Удалённый клиент"


async def anonymize_client(db: AsyncSession, user_id: int) -> bool:
    """Обезличить данные клиента. Идемпотентно: повторный вызов ничего не ломает."""
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        return False
    if user.anonymized_at is not None:
        return True

    cars = (
        await db.execute(select(Car).where(Car.client_id == user.id))
    ).scalars().all()
    car_ids = [car.id for car in cars]

    photo_filters = [Photo.uploaded_by_id == user.id]
    if car_ids:
        photo_filters.append(Photo.car_id.in_(car_ids))
    photos = (
        await db.execute(select(Photo).where(or_(*photo_filters)))
    ).scalars().all()
    for photo in photos:
        for url in (photo.url, photo.thumbnail_url):
            if url:
                delete_file_local(url)
        await db.delete(photo)

    for car in cars:
        car.license_plate = None
        car.vin = None
        car.notes = None
        car.condition_notes = None

    await db.execute(
        update(Appointment)
        .where(Appointment.client_id == user.id)
        .values(client_notes=None, master_brief=None)
    )
    await db.execute(delete(Notification).where(Notification.user_id == user.id))
    await db.execute(
        delete(UserNotificationSettings).where(
            UserNotificationSettings.user_id == user.id
        )
    )
    await db.execute(delete(LoyaltyPoints).where(LoyaltyPoints.client_id == user.id))
    await db.execute(delete(ClientDiscount).where(ClientDiscount.client_id == user.id))
    await db.execute(delete(DiscountRule).where(DiscountRule.client_id == user.id))
    await db.execute(delete(AiChatLog).where(AiChatLog.user_id == user.id))
    await db.execute(
        delete(DetailerInspection).where(DetailerInspection.client_id == user.id)
    )

    user.phone = f"del{secrets.token_hex(8)}"
    user.full_name = ANONYMIZED_NAME
    user.password = hash_password(secrets.token_urlsafe(32))
    user.anonymized_at = datetime.now(timezone.utc)

    await db.commit()
    return True
