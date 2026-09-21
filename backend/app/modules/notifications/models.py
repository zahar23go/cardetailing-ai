"""SQLAlchemy models — модуль notifications."""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.core.database import Base

class Notification(Base):
    """Уведомление для пользователя."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type = Column(String(50), nullable=False, default="info",
                  comment="appointment_reminder, appointment_cancelled, status_change, promo, info")
    channel = Column(String(20), nullable=False, default="in_app",
                     comment="in_app, telegram, sms")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    tenant = relationship("Tenant", backref="notifications")
    user = relationship("User", backref="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user={self.user_id}, type='{self.type}', read={self.is_read})>"

class UserNotificationSettings(Base):
    """Настройки уведомлений пользователя."""
    __tablename__ = "user_notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,
    )
    telegram_chat_id = Column(String(100), nullable=True)
    telegram_enabled = Column(Boolean, nullable=False, default=False)
    telegram_code = Column(String(10), nullable=True)
    sms_enabled = Column(Boolean, nullable=False, default=False)
    sms_phone = Column(String(20), nullable=True)
    notify_appointment_reminder = Column(Boolean, nullable=False, default=True)
    notify_status_change = Column(Boolean, nullable=False, default=True)
    notify_promo = Column(Boolean, nullable=False, default=False)
    remind_hours_before = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    # relationships
    user = relationship("User", backref="notification_settings")

    def __repr__(self) -> str:
        return f"<NotificationSettings(user={self.user_id}, tg={self.telegram_enabled}, sms={self.sms_enabled})>"

