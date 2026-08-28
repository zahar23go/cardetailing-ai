"""Pydantic schemas — модуль analytics."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.appointments.schemas import BoxOut

T = TypeVar("T")

class KpiOut(BaseModel):
    total_clients: int = 0
    total_masters: int = 0
    today_appointments: int = 0
    today_revenue: float = 0
    month_revenue: float = 0
    pending_appointments: int = 0
    completed_month: int = 0

class RevenuePoint(BaseModel):
    date: str
    revenue: float = 0
    appointments: int = 0

class RevenueResponse(BaseModel):
    daily: list[RevenuePoint] = []
    total: float = 0
    avg_per_day: float = 0
    best_day: Optional[str] = None
    worst_day: Optional[str] = None
    previous_total: float = 0
    change_percent: float = 0
    previous_avg_per_day: float = 0

class HeatmapCell(BaseModel):
    day: int
    hour: int
    count: int = 0
    revenue: float = 0
    box_id: Optional[int] = None

class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell] = []
    boxes: list[BoxOut] = []

class FunnelStage(BaseModel):
    name: str
    value: int = 0
    percent: float = 0
    color: str = ""

class FunnelResponse(BaseModel):
    stages: list[FunnelStage] = []
    total: int = 0
    conversion_rate: float = 0

class ServiceTrendPoint(BaseModel):
    month: str  # YYYY-MM
    revenue: float = 0
    count: int = 0

class ServiceTrend(BaseModel):
    service_id: int
    service_name: str
    category: Optional[str] = None
    monthly: list[ServiceTrendPoint] = []

class ServiceComparison(BaseModel):
    service_id: int
    service_name: str
    current_revenue: float = 0
    previous_revenue: float = 0
    change_percent: float = 0
    current_count: int = 0
    previous_count: int = 0

class TopService(BaseModel):
    service_id: int
    service_name: str
    category: Optional[str] = None
    total_revenue: float = 0
    total_count: int = 0
    avg_price: float = 0

class ForecastPoint(BaseModel):
    month: str
    forecast: float = 0
    lower_bound: float = 0
    upper_bound: float = 0

class ServiceAnalyticsResponse(BaseModel):
    trends: list[ServiceTrend] = []
    comparison: list[ServiceComparison] = []
    top_services: list[TopService] = []
    forecast: list[ForecastPoint] = []

class RevenueDetail(BaseModel):
    date: str
    service_name: str
    master_name: Optional[str] = None
    client_name: Optional[str] = None
    total_price: float = 0
    material_cost: float = 0
    profit: float = 0

class PeriodComparison(BaseModel):
    period: str  # day, week, month
    current_revenue: float = 0
    previous_revenue: float = 0
    current_count: int = 0
    previous_count: int = 0
    change_percent: float = 0

class MasterRevenueSummary(BaseModel):
    master_id: int
    master_name: str
    total_revenue: float = 0
    completed_count: int = 0
    avg_revenue: float = 0

class ServiceRevenueSummary(BaseModel):
    service_id: int
    service_name: str
    category: Optional[str] = None
    total_revenue: float = 0
    total_count: int = 0
    avg_price: float = 0

class RevenueReportResponse(BaseModel):
    total_revenue: float = 0
    total_profit: float = 0
    period_comparison: list[PeriodComparison] = []
    by_service: list[ServiceRevenueSummary] = []
    by_master: list[MasterRevenueSummary] = []
    details: list[RevenueDetail] = []

