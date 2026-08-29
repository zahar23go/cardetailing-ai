"""Pydantic schemas — модуль expenses."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class ExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., ge=0)
    category: str = Field(default="other")
    subcategory: Optional[str] = None
    payment_status: str = Field(default="paid")
    period_type: str = Field(default="monthly")
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    expense_date: Optional[str] = None
    notes: Optional[str] = None

class ExpenseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, ge=0)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    payment_status: Optional[str] = None
    period_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    expense_date: Optional[str] = None
    notes: Optional[str] = None

class ExpenseOut(BaseModel):
    id: int
    name: str
    amount: float
    category: str
    subcategory: Optional[str] = None
    payment_status: str = "paid"
    period_type: str = "monthly"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ExpenseCategoryItem(BaseModel):
    key: str
    label: str
    subcategories: list[str] = []

class ExpenseCategoryBreakdown(BaseModel):
    category: str
    label: str
    amount: float = 0
    share_percent: float = 0
    count: int = 0

class ExpenseMonthPoint(BaseModel):
    month: str
    label: str
    total: float = 0
    by_category: dict[str, float] = {}

class ExpenseInsight(BaseModel):
    type: str  # anomaly | tip | break_even | forecast
    severity: str = "info"  # info | warn | critical
    title: str
    message: str

class ExpenseAnalyticsResponse(BaseModel):
    total: float = 0
    paid_total: float = 0
    unpaid_total: float = 0
    overdue_total: float = 0
    by_category: list[ExpenseCategoryBreakdown] = []
    by_month: list[ExpenseMonthPoint] = []
    insights: list[ExpenseInsight] = []
    break_even_revenue: float = 0
    forecast_profit: float = 0
    revenue_month: float = 0

class ServiceMargin(BaseModel):
    service_id: int
    service_name: str
    category: Optional[str] = None
    total_revenue: float = 0
    total_material_cost: float = 0
    gross_profit: float = 0
    margin_percent: float = 0
    appointment_count: int = 0


class BoxMargin(BaseModel):
    box_id: Optional[int] = None
    box_name: str
    total_revenue: float = 0
    total_material_cost: float = 0
    gross_profit: float = 0
    margin_percent: float = 0
    appointment_count: int = 0
    allocated_expenses: float = 0
    net_profit: float = 0


class PLReport(BaseModel):
    # Revenue
    total_revenue: float = 0
    completed_appointments: int = 0
    avg_check: float = 0

    # Costs
    total_material_cost: float = 0
    total_expenses: float = 0
    expenses_by_category: dict[str, float] = {}

    # Profit
    gross_profit: float = 0
    gross_margin_percent: float = 0
    net_profit: float = 0
    net_margin_percent: float = 0

    # Details
    service_margins: list[ServiceMargin] = []
    box_margins: list[BoxMargin] = []
    period: str = "month"

