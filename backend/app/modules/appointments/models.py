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

# Модели Box и BoxService перенесены в app.modules.boxes.models.

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
    invoice = relationship(
        "AppointmentInvoice",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )

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


class AppointmentInvoice(Base):
    """Снимок чека в момент закрытия заезда. Не пересчитывается при смене цен каталога."""
    __tablename__ = "appointment_invoices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    box_id = Column(Integer, ForeignKey("boxes.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    service_name = Column(String(255), nullable=False, default="")
    price = Column(Numeric(10, 2), nullable=False, default=0)
    discount = Column(Numeric(10, 2), nullable=False, default=0)
    material_cost = Column(Numeric(10, 2), nullable=False, default=0, comment="Себестоимость химии на момент закрытия")
    catalog_material_cost = Column(Numeric(10, 2), nullable=False, default=0)
    shortage_qty_cost = Column(Numeric(10, 2), nullable=False, default=0)
    gross_profit = Column(Numeric(10, 2), nullable=False, default=0)
    commission_percent = Column(Integer, nullable=False, default=0, server_default="0")
    commission_amount = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    actual_time = Column(Integer, nullable=False, default=0, server_default="0", comment="Фактическая длительность заезда, мин")
    time_diff = Column(Integer, nullable=False, default=0, server_default="0", comment="Отклонение от нормы (норма − факт), мин")
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="invoice")
    box = relationship("Box")
    steps = relationship(
        "AppointmentCloseStep",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="AppointmentCloseStep.sort_order",
    )
    materials = relationship(
        "AppointmentCloseMaterial",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class AppointmentCloseStep(Base):
    """Отметка шага техкарты при закрытии."""
    __tablename__ = "appointment_close_steps"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer,
        ForeignKey("appointment_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False, default="")
    done = Column(Boolean, nullable=False, default=True)

    invoice = relationship("AppointmentInvoice", back_populates="steps")


class AppointmentCloseMaterial(Base):
    """Норма / факт / списано по материалу на заезде."""
    __tablename__ = "appointment_close_materials"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer,
        ForeignKey("appointment_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False, default="")
    unit = Column(String(20), nullable=False, default="pcs")
    norm_qty = Column(Numeric(12, 3), nullable=False, default=0)
    actual_qty = Column(Numeric(12, 3), nullable=False, default=0)
    applied_qty = Column(Numeric(12, 3), nullable=False, default=0)
    unit_cost = Column(Numeric(10, 2), nullable=False, default=0)
    line_cost = Column(Numeric(10, 2), nullable=False, default=0)
    shortage = Column(Numeric(12, 3), nullable=False, default=0)

    invoice = relationship("AppointmentInvoice", back_populates="materials")

