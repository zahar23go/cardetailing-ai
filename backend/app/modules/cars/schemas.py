"""Pydantic schemas — модуль cars."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class CarCreate(BaseModel):
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1990, le=2030)
    license_plate: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None

class CarOut(BaseModel):
    id: int
    client_id: int
    make: str
    model: str
    year: Optional[int] = None
    license_plate: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class CarUpdate(BaseModel):
    make: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1990, le=2030)
    license_plate: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None

