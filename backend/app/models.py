"""
Database models for CarDetailing AI.

SQLAlchemy ORM models: Tenant, User, Car, Service, Appointment.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    client = "client"
    master = "master"
    admin = "admin"
    super_admin = "super_admin"


class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class EntityType(str, enum.Enum):
    """Тип сущности, к которой привязано фото."""
    car = "car"
    appointment = "appointment"
    work = "work"
    portfolio = "portfolio"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False)
    logo_url = Column(Text, nullable=True)
    config = Column(JSONB, nullable=False, server_default="'{}'")
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
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    cars = relationship("Car", back_populates="tenant", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="tenant", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="tenant", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', subdomain='{self.subdomain}')>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        default=UserRole.client,
    )
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
    tenant = relationship("Tenant", back_populates="users")
    cars = relationship("Car", back_populates="client", cascade="all, delete-orphan")
    portfolio_photos = relationship(
        "Photo", back_populates="uploader", cascade="all, delete-orphan",
    )
    appointments_as_client = relationship(
        "Appointment",
        foreign_keys="Appointment.client_id",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    appointments_as_master = relationship(
        "Appointment",
        foreign_keys="Appointment.master_id",
        back_populates="master",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone='{self.phone}', role='{self.role}')>"


class Car(Base):
    __tablename__ = "cars"

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
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=True)
    license_plate = Column(String(20), nullable=True, index=True)
    color = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    client = relationship("User", back_populates="cars")
    tenant = relationship("Tenant", back_populates="cars")
    appointments = relationship("Appointment", back_populates="car")
    photos = relationship("Photo", back_populates="car", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Car(id={self.id}, {self.make} {self.model}, "
            f"plate='{self.license_plate}')>"
        )


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    duration = Column(Integer, nullable=False, comment="Duration in minutes")
    material_cost = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    appointments = relationship("Appointment", back_populates="service")
    tenant = relationship("Tenant", back_populates="services")

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name='{self.name}', price={self.price})>"


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
    tenant = relationship("Tenant", back_populates="appointments")
    photos = relationship("Photo", back_populates="appointment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, client={self.client_id}, "
            f"status='{self.status}')>"
        )


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    category = Column(
        String(50),
        nullable=False,
        default="other",
        comment="rent, salary, utilities, marketing, supplies, other",
    )
    expense_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return (
            f"<Expense(id={self.id}, name='{self.name}', "
            f"amount={self.amount}, category='{self.category}')>"
        )


class DiscountType(str, enum.Enum):
    happy_hours = "happy_hours"
    frequency = "frequency"
    win_back = "win_back"
    cashback = "cashback"


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, comment="happy_hours, frequency, win_back, cashback")
    conditions = Column(JSONB, nullable=False, server_default="'{}'")
    discount_percent = Column(Integer, nullable=False, default=0)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
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
    tenant = relationship("Tenant", backref="discount_rules")

    def __repr__(self) -> str:
        return f"<DiscountRule(id={self.id}, name='{self.name}', type='{self.type}')>"


class ClientDiscount(Base):
    __tablename__ = "client_discounts"

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
    discount_rule_id = Column(
        Integer,
        ForeignKey("discount_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    applied_percent = Column(Integer, nullable=False, default=0)
    applied_amount = Column(Numeric(10, 2), nullable=False, default=0)
    is_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # relationships
    tenant = relationship("Tenant", backref="client_discounts")
    client = relationship("User", backref="client_discounts")
    discount_rule = relationship("DiscountRule", backref="client_discounts")
    appointment = relationship("Appointment", backref="client_discounts")

    def __repr__(self) -> str:
        return f"<ClientDiscount(id={self.id}, client={self.client_id}, rule={self.discount_rule_id})>"


class LoyaltyPoints(Base):
    __tablename__ = "loyalty_points"

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
        unique=True,
    )
    balance = Column(Integer, nullable=False, default=0)
    total_earned = Column(Integer, nullable=False, default=0)
    total_spent = Column(Integer, nullable=False, default=0)
    tier = Column(String(20), nullable=False, default="bronze")
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
    tenant = relationship("Tenant", backref="loyalty_points")
    client = relationship("User", backref="loyalty_points")

    def __repr__(self) -> str:
        return f"<LoyaltyPoints(id={self.id}, client={self.client_id}, balance={self.balance})>"


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
    uploaded_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=True)
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
    uploader = relationship("User", back_populates="portfolio_photos", foreign_keys=[uploaded_by_id])

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, type='{self.entity_type}', url='{self.url}')>"


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
    remind_hours_before = Column(Integer, nullable=False, default=24)
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


class LoyaltyTierConfig(Base):
    """Конфигурация уровней лояльности."""
    __tablename__ = "loyalty_tier_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tier = Column(String(20), nullable=False, comment="bronze, silver, gold, platinum")
    min_total_spent = Column(Integer, nullable=False, default=0)
    min_visits = Column(Integer, nullable=False, default=0)
    discount_percent = Column(Integer, nullable=False, default=0)
    bonus_multiplier = Column(Integer, nullable=False, default=1,
                              comment="Множитель начисления баллов (1x, 1.5x, 2x)")
    color = Column(String(7), nullable=False, default="#CD7F32",
                   comment="Цвет уровня: #CD7F32 bronze, #C0C0C0 silver, #FFD700 gold")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", backref="loyalty_tier_configs")

    def __repr__(self) -> str:
        return f"<TierConfig(tenant={self.tenant_id}, tier='{self.tier}', discount={self.discount_percent}%)>"


class Payment(Base):
    """Платёж по записи."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending",
                    comment="pending, succeeded, failed, refunded")
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(255), nullable=True, comment="ID в платёжной системе")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    tenant = relationship("Tenant", backref="payments")
    appointment = relationship("Appointment", backref="payment")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, appt={self.appointment_id}, {self.amount} руб, {self.status})>"
