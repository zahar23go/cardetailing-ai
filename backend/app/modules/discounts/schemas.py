"""Pydantic schemas — модуль discounts."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.analytics.schemas import HeatmapCell

T = TypeVar("T")

class DiscountRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="happy_hours, frequency, win_back, weather, cashback, service, client")
    conditions: Optional[dict] = None
    discount_percent: int = Field(default=0, ge=0, le=100)
    slot_start: Optional[str] = Field(None, description="Время начала слота HH:MM (для happy_hours)")
    slot_end: Optional[str] = Field(None, description="Время конца слота HH:MM (для happy_hours)")
    service_id: Optional[int] = Field(None, description="ID услуги (для скидки на услугу)")
    client_id: Optional[int] = Field(None, description="ID клиента (для персональной скидки)")
    valid_until: Optional[str] = Field(None, description="Срок действия YYYY-MM-DD")
    is_active: Optional[bool] = True

class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    conditions: Optional[dict] = None
    discount_percent: Optional[int] = Field(None, ge=0, le=100)
    slot_start: Optional[str] = Field(None, description="Время начала слота HH:MM (для happy_hours)")
    slot_end: Optional[str] = Field(None, description="Время конца слота HH:MM (для happy_hours)")
    service_id: Optional[int] = None
    client_id: Optional[int] = None
    valid_until: Optional[str] = None
    is_active: Optional[bool] = None

class DiscountRuleOut(BaseModel):
    id: int
    name: str
    type: str
    conditions: Optional[dict] = None
    discount_percent: int
    slot_start: Optional[str] = None
    slot_end: Optional[str] = None
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    valid_until: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ClientDiscountOut(BaseModel):
    id: int
    client_id: int
    discount_rule_id: int
    appointment_id: Optional[int] = None
    applied_percent: int
    applied_amount: float
    is_used: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class DiscountAnalyticsTopRule(BaseModel):
    rule_id: int
    rule_name: str
    rule_type: str
    times_used: int = 0
    total_discount: float = 0
    client_count: int = 0

class DiscountAnalyticsResponse(BaseModel):
    total_rules: int = 0
    active_rules: int = 0
    total_times_used: int = 0
    total_discount_amount: float = 0
    unique_clients_affected: int = 0
    top_rules: list[DiscountAnalyticsTopRule] = []

class DiscountSuggestion(BaseModel):
    key: str
    name: str
    hour_start: str
    hour_end: str
    weekdays: list[int]
    weekday_label: str
    discount_percent: int
    avg_load: float
    reason: str

class DiscountRuleAdvice(BaseModel):
    rule_id: int | None = None
    rule_name: str
    action: str  # create | increase | decrease | disable | keep
    message: str
    suggested_percent: int | None = None

class DiscountRoiItem(BaseModel):
    rule_id: int
    rule_name: str
    times_used: int = 0
    discount_cost: float = 0
    estimated_extra_revenue: float = 0
    roi_percent: float = 0
    verdict: str

class DiscountBeforeAfterPoint(BaseModel):
    rule_id: int
    rule_name: str
    label: str
    before_avg: float = 0
    after_avg: float = 0

class DiscountIntelligenceResponse(BaseModel):
    period_days: int = 60
    cells: list[HeatmapCell] = []
    suggestions: list[DiscountSuggestion] = []
    recommendations: list[DiscountRuleAdvice] = []
    roi: list[DiscountRoiItem] = []
    before_after: list[DiscountBeforeAfterPoint] = []

class ServiceDiscountRecOut(BaseModel):
    id: int
    service_id: int
    service_name: str
    price: float = 0
    cost_price: float = 0
    bookings_30d: int = 0
    bookings_prev_30d: int = 0
    popularity_index: float = 0
    margin_raw: float = 0
    margin_index: float = 0
    priority: float = 0
    suggested_percent: int = 0
    adjusted_percent: Optional[int] = None
    scenario: str = "priority"
    reason: str = ""
    status: str = "pending"
    discount_rule_id: Optional[int] = None
    computed_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None

class ServiceDiscountRecDecision(BaseModel):
    action: str = Field(..., description="approve | reject | adjust")
    adjusted_percent: Optional[int] = Field(None, ge=1, le=50)

class ServiceDiscountRecAnalyticsPoint(BaseModel):
    service_id: int
    service_name: str
    before_bookings: int = 0
    after_bookings: int = 0
    bookings_growth_percent: float = 0
    before_revenue: float = 0
    after_revenue: float = 0
    revenue_delta: float = 0

class ServiceDiscountRecsResponse(BaseModel):
    last_computed_at: Optional[datetime] = None
    next_refresh_at: Optional[datetime] = None
    auto_refreshed: bool = False
    items: list[ServiceDiscountRecOut] = []
    analytics: list[ServiceDiscountRecAnalyticsPoint] = []

class LoyaltyPointsOut(BaseModel):
    id: int
    client_id: int
    balance: int
    total_earned: int
    total_spent: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class LoyaltyPointsSummary(BaseModel):
    client_id: int
    full_name: str
    phone: str
    balance: int
    total_earned: int
    total_spent: int

class LoyaltyTierConfigOut(BaseModel):
    id: int
    tier: str
    min_total_spent: int = 0
    min_visits: int = 0
    discount_percent: int = 0
    bonus_multiplier: int = 1
    color: str = "#CD7F32"

    model_config = {"from_attributes": True}

class LoyaltyTierConfigUpdate(BaseModel):
    tier: str
    min_total_spent: int = 0
    min_visits: int = 0
    discount_percent: int = 0
    bonus_multiplier: int = 1
    color: str = "#CD7F32"

class ClientTierOut(BaseModel):
    client_id: int
    full_name: str
    phone: str
    tier: str = "bronze"
    total_spent: int = 0
    total_visits: int = 0
    points_balance: int = 0
    next_tier: Optional[str] = None
    next_tier_progress: float = 0.0
    next_tier_remaining: int = 0


DiscountIntelligenceResponse.model_rebuild()

