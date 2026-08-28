"""SQLAlchemy models — модуль expenses."""
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
        comment="rent, salary, utilities, marketing, supplies, equipment, taxes, insurance, software, transport, other",
    )
    subcategory = Column(String(100), nullable=True)
    payment_status = Column(
        String(30),
        nullable=False,
        default="paid",
        comment="paid, unpaid, overdue, partial",
    )
    period_type = Column(
        String(30),
        nullable=False,
        default="monthly",
        comment="monthly, quarterly, yearly, one_time",
    )
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
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
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relationships
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return (
            f"<Expense(id={self.id}, name='{self.name}', "
            f"amount={self.amount}, category='{self.category}')>"
        )

