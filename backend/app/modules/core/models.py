"""SQLAlchemy models — модуль core."""
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

class UserRole(str, enum.Enum):
    client = "client"
    master = "master"
    admin = "admin"
    super_admin = "super_admin"

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False)
    logo_url = Column(Text, nullable=True)
    config = Column(JSONB, nullable=False, server_default="'{}'")
    plan = Column(String(20), nullable=False, default="business", server_default="business")
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
    boxes = relationship("Box", back_populates="tenant", cascade="all, delete-orphan")
    materials = relationship("Material", back_populates="tenant", cascade="all, delete-orphan")
    tech_cards = relationship("TechCard", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

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
    commission_percent = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Базовая комиссия мастера, % от цены заезда",
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


class MasterSkill(Base):
    """Какие услуги/техкарты делает мастер и комиссия по ним."""
    __tablename__ = "master_skills"
    __table_args__ = (
        UniqueConstraint("master_id", "service_id", name="uq_master_skills_master_service"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    master_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id = Column(
        Integer,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commission_percent = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    master = relationship("User", backref="master_skills")
    service = relationship("Service")

    def __repr__(self) -> str:
        return f"<MasterSkill(master={self.master_id}, service={self.service_id})>"

