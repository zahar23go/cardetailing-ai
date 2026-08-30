"""SQLAlchemy models — модуль cars."""
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
    vin = Column(String(17), nullable=True, index=True)
    body_type = Column(String(40), nullable=True)
    mileage = Column(Integer, nullable=True)
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

