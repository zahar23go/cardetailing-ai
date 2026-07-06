"""
Database models for CarDetailing AI.

SQLAlchemy ORM models: User, Car, Service, Appointment.
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
from sqlalchemy.orm import relationship
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(
        Enum(UserRole),
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
    cars = relationship("Car", back_populates="client", cascade="all, delete-orphan")
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
        return f"<User(id={self.id}, phone='{self.phone}', role='{self.role.value}')>"


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
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
    appointments = relationship("Appointment", back_populates="car")

    def __repr__(self) -> str:
        return (
            f"<Car(id={self.id}, {self.make} {self.model}, "
            f"plate='{self.license_plate}')>"
        )


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
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

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name='{self.name}', price={self.price})>"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
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
        Enum(AppointmentStatus),
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

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, client={self.client_id}, "
            f"status='{self.status.value}')>"
        )
