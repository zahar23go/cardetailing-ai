"""SQLAlchemy models — модуль discounts."""
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

class DiscountType(str, enum.Enum):
    happy_hours = "happy_hours"
    service = "service"
    client = "client"
    segment = "segment"
    frequency = "frequency"
    win_back = "win_back"
    cashback = "cashback"
    weather = "weather"

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
    type = Column(String(50), nullable=False, comment="happy_hours, frequency, win_back, weather, cashback, service, client")
    conditions = Column(JSONB, nullable=False, server_default="'{}'")
    discount_percent = Column(Integer, nullable=False, default=0)
    slot_start = Column(Time(timezone=False), nullable=True, comment="Время начала слота (HH:MM)")
    slot_end = Column(Time(timezone=False), nullable=True, comment="Время конца слота (HH:MM)")
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True,
        comment="Привязка скидки к услуге",
    )
    client_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True,
        comment="Персональная скидка для клиента",
    )
    valid_until = Column(DateTime(timezone=True), nullable=True, comment="Срок действия скидки")
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
    service = relationship("Service", backref="discount_rules")
    client = relationship("User", backref="personal_discounts", foreign_keys=[client_id])

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

class ServiceDiscountRecommendation(Base):
    """Еженедельные рекомендации скидок по услугам (маржа × популярность)."""
    __tablename__ = "service_discount_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    period_days = Column(Integer, nullable=False, default=30)
    bookings_30d = Column(Integer, nullable=False, default=0)
    bookings_prev_30d = Column(Integer, nullable=False, default=0)
    popularity_index = Column(Float, nullable=False, default=0)
    margin_raw = Column(Float, nullable=False, default=0)
    margin_index = Column(Float, nullable=False, default=0)
    priority = Column(Float, nullable=False, default=0)
    suggested_percent = Column(Integer, nullable=False, default=0)
    scenario = Column(String(50), nullable=False, default="priority")
    reason = Column(Text, nullable=False, default="")
    status = Column(String(30), nullable=False, default="pending", index=True)
    adjusted_percent = Column(Integer, nullable=True)
    discount_rule_id = Column(
        Integer, ForeignKey("discount_rules.id", ondelete="SET NULL"), nullable=True,
    )
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    service = relationship("Service")
    discount_rule = relationship("DiscountRule")

