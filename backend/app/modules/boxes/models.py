"""SQLAlchemy models — модуль boxes (боксы/зоны сервиса)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Box(Base):
    """Бокс/зона в сервисе (напр. «Бокс 1 — мойка», «Бокс 2 — полировка»).

    Занятость бокса не хранится денормализованно: она вычисляется
    динамически по активным Appointment (см. appointments.live_service).
    """

    __tablename__ = "boxes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False, comment="Название бокса")
    color = Column(String(20), nullable=True, comment="Цвет для UI (hex)")
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    tenant = relationship("Tenant", back_populates="boxes")
    appointments = relationship("Appointment", back_populates="box")
    box_services = relationship("BoxService", back_populates="box", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Box(id={self.id}, name='{self.name}')>"


class BoxService(Base):
    """Привязка услуг к боксам."""

    __tablename__ = "box_services"

    id = Column(Integer, primary_key=True, index=True)
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # relationships
    box = relationship("Box", back_populates="box_services")
    service = relationship("Service")

    def __repr__(self) -> str:
        return f"<BoxService(box_id={self.box_id}, service_id={self.service_id})>"
