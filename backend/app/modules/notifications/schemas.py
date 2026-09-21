"""Pydantic schemas — модуль notifications."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class NotificationOut(BaseModel):
    id: int
    type: str
    channel: str
    title: str
    message: str
    is_read: bool = False
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class UnreadCountOut(BaseModel):
    count: int = 0

class NotificationSettingsOut(BaseModel):
    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    sms_enabled: bool = False
    sms_phone: Optional[str] = None
    notify_appointment_reminder: bool = True
    notify_status_change: bool = True
    notify_promo: bool = False
    remind_hours_before: int = 1

    model_config = {"from_attributes": True}

class NotificationSettingsUpdate(BaseModel):
    telegram_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    sms_phone: Optional[str] = None
    notify_appointment_reminder: Optional[bool] = None
    notify_status_change: Optional[bool] = None
    notify_promo: Optional[bool] = None
    remind_hours_before: Optional[int] = Field(None, ge=1, le=168)

class TelegramConnectRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)

