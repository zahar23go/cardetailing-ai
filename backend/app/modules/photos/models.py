"""SQLAlchemy models — модуль photos."""
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

class EntityType(str, enum.Enum):
    """Тип сущности, к которой привязано фото."""
    car = "car"
    appointment = "appointment"
    work = "work"
    portfolio = "portfolio"

class Photo(Base):
    """Фотография, привязанная к сущности (авто, запись, портфолио)."""
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type = Column(String(20), nullable=False, index=True)
    car_id = Column(
        Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Привязка к услуге (для портфолио)",
    )
    uploaded_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True, comment="Описание работы (было → стало)")
    is_primary = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    tenant = relationship("Tenant", backref="photos")
    car = relationship("Car", back_populates="photos")
    appointment = relationship("Appointment", back_populates="photos")
    service = relationship("Service", backref="portfolio_photos")
    uploader = relationship("User", back_populates="portfolio_photos", foreign_keys=[uploaded_by_id])

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, type='{self.entity_type}', url='{self.url}')>"

