"""SQLAlchemy models — модуль payments."""
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

