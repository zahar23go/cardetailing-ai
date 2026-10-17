"""SQLAlchemy models — AI-детейлер."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AiChatLog(Base):
    """Один ход диалога с ИИ-ассистентом: вопрос, ответ, инструменты, время ответа.

    Пишется из ``run_consultant_chat`` для всех ассистентов (detailer, financier,
    manager, admin). Текст хранится ограниченное время (AI_CHAT_RETENTION_DAYS).
    """

    __tablename__ = "ai_chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id = Column(String(64), nullable=False, index=True)
    assistant = Column(String(32), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tool_calls = Column(JSONB, nullable=False, server_default="'[]'")
    duration_ms = Column(Integer, nullable=False, server_default="0")
    is_error = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class DetailerInspection(Base):
    """Сессия осмотра: метки/фото → допродажи, слот, сводка мастеру."""

    __tablename__ = "detailer_inspections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"), nullable=True, index=True)
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    primary_service_id = Column(
        Integer,
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )
    suggested_box_id = Column(
        Integer,
        ForeignKey("boxes.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
    master_brief = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=False, server_default="'[]'")
    findings = Column(JSONB, nullable=False, server_default="'[]'")
    upsells = Column(JSONB, nullable=False, server_default="'[]'")
    slots = Column(JSONB, nullable=False, server_default="'[]'")
    photo_ids = Column(JSONB, nullable=False, server_default="'[]'")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("User", foreign_keys=[client_id])
    car = relationship("Car", foreign_keys=[car_id])
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    primary_service = relationship("Service", foreign_keys=[primary_service_id])
    suggested_box = relationship("Box", foreign_keys=[suggested_box_id])
