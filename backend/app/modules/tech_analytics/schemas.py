"""Pydantic schemas — модуль tech_analytics."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class PurchaseRecommendOut(BaseModel):
    material_id: int
    material_name: str
    sku: Optional[str] = None
    category: str
    unit: str
    quantity: float
    min_quantity: float
    avg_daily_consumption: float = 0
    days_of_stock: Optional[float] = None
    target_quantity: float
    recommend_qty: float
    purchase_price: float = 0
    estimate_cost: float = 0
    supplier: Optional[str] = None
    priority: str
    reason: str

class AuditServiceBreakout(BaseModel):
    service_id: int
    service_name: str
    completed_count: int = 0
    norm_per_service: float = 0
    norm_total: float = 0

class ConsumptionAuditOut(BaseModel):
    material_id: int
    material_name: str
    sku: Optional[str] = None
    category: str
    unit: str
    purchase_price: float = 0
    norm_qty: float = 0
    fact_qty: float = 0
    variance_qty: float = 0
    variance_percent: Optional[float] = None
    norm_cost: float = 0
    fact_cost: float = 0
    variance_cost: float = 0
    status: str
    status_label: str
    services: list[AuditServiceBreakout] = []

class TechAnalyticsSummaryOut(BaseModel):
    period_days: int = 30
    cover_days: int = 30
    purchase_items: int = 0
    purchase_estimate_cost: float = 0
    purchase_critical: int = 0
    audit_items: int = 0
    audit_overspend: int = 0
    audit_underspend: int = 0
    audit_variance_cost: float = 0
    anomaly_count: int = 0
    open_audit_logs: int = 0

class AnomalyOut(BaseModel):
    code: str
    severity: str
    material_id: int
    material_name: str
    unit: str
    title: str
    message: str
    metric_value: float = 0
    cost_impact: float = 0
    fingerprint: str

class AuditLogOut(BaseModel):
    id: int
    kind: str
    severity: str
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    title: str
    message: Optional[str] = None
    payload: dict = {}
    status: str
    fingerprint: str
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class AuditSyncResultOut(BaseModel):
    created: int = 0
    updated: int = 0
    resolved: int = 0
    open_total: int = 0
    recommendations: int = 0
    audit_rows: int = 0
    anomalies: int = 0

