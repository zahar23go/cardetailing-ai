"""HTTP API — модуль notifications."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Body, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import (
    get_current_user as _get_current_user,
    require_admin as _require_admin,
    require_master as _require_master,
    hash_password as _hash_password,
    verify_password as _verify_password,
    create_token as _create_token,
)
from app.core.endpoint_helpers import *  # noqa: F401,F403
from app.core.image_service import (
    validate_image,
    save_file_local,
    generate_filename,
    delete_file_local,
    resolve_portfolio_url,
)
from app.core.deepseek_client import get_ai_response, get_financier_response, get_consultant_response
from app.models import *  # noqa: F401,F403
from app.schemas import *  # noqa: F401,F403

router = APIRouter()

@router.get("/api/notifications", response_model=PaginatedResponse[NotificationOut])
async def get_notifications(
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список уведомлений."""
    from app.core.notification_service import get_notifications as _get_notifs
    items, total = await _get_notifs(
        db, current_user["id"], UUID(current_user["tenant_id"]),
        skip=skip, limit=limit, unread_only=unread_only,
    )
    return PaginatedResponse[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        total=total, skip=skip, limit=limit,
    )

@router.get("/api/notifications/unread-count", response_model=UnreadCountOut)
async def get_unread_count(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить количество непрочитанных уведомлений."""
    from app.core.notification_service import get_unread_count as _count
    count = await _count(db, current_user["id"], UUID(current_user["tenant_id"]))
    return UnreadCountOut(count=count)

@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить уведомление как прочитанное."""
    from app.core.notification_service import mark_as_read
    ok = await mark_as_read(db, notification_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    return {"message": "Уведомление отмечено как прочитанное"}

@router.put("/api/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить все уведомления как прочитанные."""
    from app.core.notification_service import mark_all_as_read
    count = await mark_all_as_read(db, current_user["id"], UUID(current_user["tenant_id"]))
    return {"message": f"Отмечено {count} уведомлений как прочитанные", "count": count}

@router.get("/api/notifications/settings", response_model=NotificationSettingsOut)
async def get_notification_settings(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить настройки уведомлений."""
    from app.core.notification_service import get_settings
    settings = await get_settings(db, current_user["id"])
    if not settings:
        return NotificationSettingsOut()
    return NotificationSettingsOut.model_validate(settings)

@router.put("/api/notifications/settings", response_model=NotificationSettingsOut)
async def update_notification_settings(
    request: NotificationSettingsUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить настройки уведомлений."""
    from app.core.notification_service import upsert_settings
    data = request.model_dump(exclude_unset=True)
    settings = await upsert_settings(db, current_user["id"], **data)
    return NotificationSettingsOut.model_validate(settings)

@router.post("/api/telegram/connect")
async def connect_telegram(
    request: TelegramConnectRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Подключить Telegram по коду."""
    from app.core.notification_service import upsert_settings
    # В реальном приложении здесь проверка кода из Telegram Bot
    settings = await upsert_settings(
        db, current_user["id"],
        telegram_enabled=True,
        telegram_chat_id=f"user_{current_user['id']}",
        telegram_code=request.code,
    )
    return {"message": "Telegram подключён", "chat_id": settings.telegram_chat_id}

@router.post("/api/telegram/disconnect")
async def disconnect_telegram(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отключить Telegram."""
    from app.core.notification_service import upsert_settings
    await upsert_settings(
        db, current_user["id"],
        telegram_enabled=False,
        telegram_chat_id=None,
    )
    return {"message": "Telegram отключён"}

@router.post("/api/telegram/webhook")
async def telegram_webhook(
    data: dict,
):
    """Webhook для Telegram бота."""
    from app.core.telegram_service import handle_telegram_webhook
    return await handle_telegram_webhook(data)

