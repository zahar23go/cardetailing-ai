"""SQLAlchemy models — модуль appointments."""
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

class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class Box(Base):
    """Бокс/зона в сервисе (напр. «Бокс 1 — мойка», «Бокс 2 — полировка»)."""
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

class Appointment(Base):
    __tablename__ = "appointments"

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
    master_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    car_id = Column(
        Integer,
        ForeignKey("cars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id = Column(
        Integer,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    box_id = Column(
        Integer,
        ForeignKey("boxes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Бокс/зона выполнения",
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default=AppointmentStatus.pending,
        index=True,
    )
    total_price = Column(Numeric(10, 2), nullable=False, default=0)
    discount_applied = Column(Numeric(10, 2), nullable=False, default=0)
    client_notes = Column(Text, nullable=True)
    master_brief = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relationships
    client = relationship(
        "User",
        foreign_keys=[client_id],
        back_populates="appointments_as_client",
    )
    master = relationship(
        "User",
        foreign_keys=[master_id],
        back_populates="appointments_as_master",
    )
    car = relationship("Car", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    box = relationship("Box", back_populates="appointments")
    tenant = relationship("Tenant", back_populates="appointments")
    photos = relationship("Photo", back_populates="appointment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, client={self.client_id}, "
            f"status='{self.status}')>"
        )

class WorkingHours(Base):
    """Рабочие часы мастера."""
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    day_of_week = Column(Integer, nullable=False, comment="0=Mon ... 6=Sun")
    start_time = Column(String(5), nullable=False, default="09:00")
    end_time = Column(String(5), nullable=False, default="18:00")
    is_working_day = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    master = relationship("User", backref="working_hours")
    tenant = relationship("Tenant", backref="working_hours")

    def __repr__(self) -> str:
        return f"<WorkingHours(master={self.master_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"

class AppointmentHistory(Base):
    """История изменений записи."""
    __tablename__ = "appointment_history"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    changed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    change_type = Column(
        String(20), nullable=False, default="update",
        comment="create, update, cancel, move, status_change",
    )
    field_name = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    appointment = relationship("Appointment", backref="history_entries")
    changed_by = relationship("User", backref="history_entries")

    def __repr__(self) -> str:
        return f"<History(appt={self.appointment_id}, type='{self.change_type}', field='{self.field_name}')>"

