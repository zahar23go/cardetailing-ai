"""Pydantic schemas — модуль services."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = None
    price: float = Field(default=0, ge=0)
    duration: int = Field(default=60, ge=1)
    material_cost: float = Field(default=0, ge=0)
    cost_price: float = Field(default=0, ge=0, description="Себестоимость")

class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=1)
    material_cost: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

class ServiceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float
    duration: int
    material_cost: float
    cost_price: float = 0
    margin_percent: float = 0
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

