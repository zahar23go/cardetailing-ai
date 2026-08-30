"""Pydantic schemas — модуль tech_cards."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class TechCardItemIn(BaseModel):
    material_id: int
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None

class TechCardItemOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    material_unit: str
    material_sku: Optional[str] = None
    purchase_price: float = 0
    stock_quantity: float = 0
    quantity: float
    line_cost: float = 0
    notes: Optional[str] = None
    is_low_stock: bool = False

    model_config = {"from_attributes": True}

class TechCardBlockIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(0, ge=0, le=24 * 60)
    photo_url: Optional[str] = None
    items: list[TechCardItemIn] = Field(default_factory=list)

class TechCardBlockOut(BaseModel):
    id: int
    sort_order: int = 0
    title: str
    description: Optional[str] = None
    duration_minutes: int = 0
    photo_url: Optional[str] = None
    items: list[TechCardItemOut] = []
    items_count: int = 0
    estimated_cost: float = 0

    model_config = {"from_attributes": True}

class TechCardCreate(BaseModel):
    service_id: int
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: bool = True
    items: list[TechCardItemIn] = Field(default_factory=list)
    blocks: list[TechCardBlockIn] = Field(default_factory=list)

class TechCardUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    items: Optional[list[TechCardItemIn]] = None
    blocks: Optional[list[TechCardBlockIn]] = None

class TechCardOut(BaseModel):
    id: int
    service_id: int
    service_name: str
    service_price: float = 0
    name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    items: list[TechCardItemOut] = []
    items_count: int = 0
    estimated_cost: float = 0
    blocks: list[TechCardBlockOut] = []
    blocks_count: int = 0
    total_duration_minutes: int = 0
    current_version: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class TechCardReorderIn(BaseModel):
    block_ids: list[int]

class TechCardPhotoOut(BaseModel):
    url: str
    thumbnail_url: Optional[str] = None


class TechCardVersionOut(BaseModel):
    id: int
    version_no: int
    created_at: Optional[datetime] = None
    blocks_count: int = 0
    items_count: int = 0
    estimated_cost: float = 0
    name: Optional[str] = None


class TechCardVersionDetailOut(TechCardVersionOut):
    snapshot: dict = {}

