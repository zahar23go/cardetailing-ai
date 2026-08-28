"""Pydantic schemas — модуль payments."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class PaymentCreateRequest(BaseModel):
    appointment_id: int
    payment_method: Optional[str] = "card"

class PaymentOut(BaseModel):
    id: int
    appointment_id: int
    amount: float
    status: str
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class PaymentWebhookRequest(BaseModel):
    event: str
    payment_id: str
    status: str
    amount: float = 0

