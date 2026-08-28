"""SQLAlchemy models — модуль services."""
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
    cost_price = Column(Numeric(10, 2), nullable=False, default=0, comment="Себестоимость услуги")
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

