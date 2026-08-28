"""Pydantic schemas — модуль inventory."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class MaterialMovementOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    material_unit: str
    movement_type: str
    movement_type_label: str
    delta: float
    quantity_before: float
    quantity_after: float
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

class StockHistoryPoint(BaseModel):
    date: str
    quantity: float
    value: float = 0

class AbcItemOut(BaseModel):
    material_id: int
    material_name: str
    category: str
    unit: str
    consumption_qty: float = 0
    consumption_value: float = 0
    stock_value: float = 0
    metric_value: float = 0
    share_percent: float = 0
    cumulative_percent: float = 0
    abc_class: str
    quantity: float = 0
    min_quantity: float = 0
    is_low_stock: bool = False

class CriticalItemOut(BaseModel):
    material_id: int
    material_name: str
    sku: Optional[str] = None
    category: str
    unit: str
    quantity: float
    min_quantity: float
    deficit: float
    purchase_price: float = 0
    restock_cost: float = 0
    supplier: Optional[str] = None

class InventorySummaryOut(BaseModel):
    materials_count: int = 0
    stock_value: float = 0
    critical_count: int = 0
    movements_period: int = 0
    period_days: int = 30

