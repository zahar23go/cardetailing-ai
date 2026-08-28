"""Pydantic schemas — модуль materials."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

MATERIAL_CATEGORIES = ("chemistry", "consumables", "inventory", "workwear", "other")

MATERIAL_UNITS = ("pcs", "ml", "l", "g", "kg", "m", "pack")

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    category: str = Field(default="other")
    unit: str = Field(default="pcs")
    quantity: float = Field(default=0, ge=0)
    min_quantity: float = Field(default=0, ge=0)
    purchase_price: float = Field(default=0, ge=0)
    supplier: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in MATERIAL_CATEGORIES:
            raise ValueError(f"category must be one of {MATERIAL_CATEGORIES}")
        return v

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v not in MATERIAL_UNITS:
            raise ValueError(f"unit must be one of {MATERIAL_UNITS}")
        return v

class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = Field(None, ge=0)
    min_quantity: Optional[float] = Field(None, ge=0)
    purchase_price: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MATERIAL_CATEGORIES:
            raise ValueError(f"category must be one of {MATERIAL_CATEGORIES}")
        return v

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MATERIAL_UNITS:
            raise ValueError(f"unit must be one of {MATERIAL_UNITS}")
        return v

class MaterialOut(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    category: str
    unit: str
    quantity: float
    min_quantity: float
    purchase_price: float
    supplier: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    is_low_stock: bool = False
    stock_value: float = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class MaterialCategoryItem(BaseModel):
    key: str
    label: str

