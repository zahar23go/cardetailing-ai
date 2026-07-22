"""
Pydantic schemas for request/response validation.

Replaces manual dict extraction in endpoint handlers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# GENERIC PAGINATION
# =============================================================================

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    All list endpoints return this shape:
      { "items": [...], "total": N, "skip": 0, "limit": 20 }
    """
    items: list[T]
    total: int
    skip: int = 0
    limit: int = 20


# =============================================================================
# TENANTS
# =============================================================================

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subdomain: str = Field(..., min_length=1, max_length=100)
    logo_url: Optional[str] = None
    config: Optional[dict] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subdomain: Optional[str] = Field(None, min_length=1, max_length=100)
    logo_url: Optional[str] = None
    config: Optional[dict] = None


class TenantOut(BaseModel):
    id: UUID
    name: str
    subdomain: str
    logo_url: Optional[str] = None
    config: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# AUTH
# =============================================================================

class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=4, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=150)
    tenant_id: Optional[UUID] = Field(None, description="Tenant UUID (required for client registration)")


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    id: int
    phone: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# =============================================================================
# SERVICES
# =============================================================================

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = None
    price: float = Field(default=0, ge=0)
    duration: int = Field(default=60, ge=1)
    material_cost: float = Field(default=0, ge=0)


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=1)
    material_cost: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ServiceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float
    duration: int
    material_cost: float
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# CARS
# =============================================================================

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


# =============================================================================
# APPOINTMENTS
# =============================================================================

class AppointmentCreate(BaseModel):
    service_id: int
    car_id: int
    start_time: str = Field(..., description="ISO 8601 datetime string")
    notes: Optional[str] = Field(None, description="Client notes")
    client_notes: Optional[str] = None  # alias for notes
    box_id: Optional[int] = Field(None, description="ID бокса/зоны")

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("start_time must be a valid ISO 8601 string")
        return v


class AppointmentStatusUpdate(BaseModel):
    status: Optional[str] = None
    master_id: Optional[int] = None
    master_brief: Optional[str] = None


class MasterStatusUpdate(BaseModel):
    status: str = Field(..., description="New status (in_progress or completed)")


class ClientAppointmentEdit(BaseModel):
    """Client can edit date/time/car of their pending/confirmed appointment."""
    start_time: Optional[str] = Field(None, description="ISO 8601 datetime string")
    car_id: Optional[int] = None
    client_notes: Optional[str] = None

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("start_time must be a valid ISO 8601 string")
        return v


class MasterNotesUpdate(BaseModel):
    master_brief: str = Field(..., min_length=1)
    notes: Optional[str] = None  # alias


class ClientRef(BaseModel):
    id: int
    full_name: str
    phone: str

    model_config = {"from_attributes": True}


class MasterRef(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class CarRef(BaseModel):
    id: int
    make: str
    model: str
    license_plate: Optional[str] = None

    model_config = {"from_attributes": True}


class ServiceRef(BaseModel):
    id: int
    name: str
    price: float

    model_config = {"from_attributes": True}


class AppointmentOut(BaseModel):
    id: int
    client_id: int
    master_id: Optional[int] = None
    car_id: int
    service_id: int
    box_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    total_price: float = 0
    discount_applied: float = 0
    client_notes: Optional[str] = None
    master_brief: Optional[str] = None
    service_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    client: Optional[ClientRef] = None
    master: Optional[MasterRef] = None
    car: Optional[CarRef] = None
    service: Optional[ServiceRef] = None

    model_config = {"from_attributes": True}


# =============================================================================
# USERS
# =============================================================================

class UserListOut(BaseModel):
    id: int
    phone: str
    full_name: str
    role: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="New role: client, master, admin, super_admin")


class UserDetailOut(BaseModel):
    id: int
    phone: str
    full_name: str
    role: str
    created_at: Optional[datetime] = None
    appointments_count: int = 0
    total_spent: float = 0
    last_visit: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# ANALYTICS
# =============================================================================

class KpiOut(BaseModel):
    total_clients: int = 0
    total_masters: int = 0
    today_appointments: int = 0
    today_revenue: float = 0
    month_revenue: float = 0
    pending_appointments: int = 0
    completed_month: int = 0


# =============================================================================
# AI CHAT
# =============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str


# =============================================================================
# AI FINANCIER
# =============================================================================

class FinancierRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class FinancierResponse(BaseModel):
    response: str


# =============================================================================
# EXPENSES & P&L
# =============================================================================

class ExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., ge=0)
    category: str = Field(default="other", description="rent, salary, utilities, marketing, supplies, other")
    expense_date: Optional[str] = None
    notes: Optional[str] = None


class ExpenseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, ge=0)
    category: Optional[str] = None
    expense_date: Optional[str] = None
    notes: Optional[str] = None


class ExpenseOut(BaseModel):
    id: int
    name: str
    amount: float
    category: str
    expense_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ServiceMargin(BaseModel):
    service_id: int
    service_name: str
    category: Optional[str] = None
    total_revenue: float = 0
    total_material_cost: float = 0
    gross_profit: float = 0
    margin_percent: float = 0
    appointment_count: int = 0


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
    period: str = "month"


# =============================================================================
# ANALYTICS CHARTS
# =============================================================================

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
    boxes: list["BoxOut"] = []


class BoxCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class BoxUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class BoxOut(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FunnelStage(BaseModel):
    name: str
    value: int = 0
    percent: float = 0
    color: str = ""


class FunnelResponse(BaseModel):
    stages: list[FunnelStage] = []
    total: int = 0
    conversion_rate: float = 0


# =============================================================================
# RFM SEGMENTATION
# =============================================================================

class RfmClient(BaseModel):
    id: int
    full_name: str
    phone: str
    recency_days: int = 999
    frequency: int = 0
    monetary: float = 0
    segment: str = "new"
    last_visit: Optional[str] = None
    created_at: Optional[str] = None


class SegmentCount(BaseModel):
    segment: str
    count: int = 0
    total_revenue: float = 0
    percent: float = 0


class RfmResponse(BaseModel):
    clients: list[RfmClient] = []
    segments: list[SegmentCount] = []
    total: int = 0


# =============================================================================
# DISCOUNTS & LOYALTY
# =============================================================================

class DiscountRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="happy_hours, frequency, win_back, cashback, service, client")
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


# =============================================================================
# PHOTOS
# =============================================================================

class PhotoOut(BaseModel):
    id: int
    entity_type: str
    url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    uploader_name: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PhotoOrderUpdate(BaseModel):
    sort_order: int = Field(..., ge=0)


class PhotoCreateResponse(BaseModel):
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    message: str = "Фото загружено"


# =============================================================================
# NOTIFICATIONS
# =============================================================================

class NotificationOut(BaseModel):
    id: int
    type: str
    channel: str
    title: str
    message: str
    is_read: bool = False
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    count: int = 0


class NotificationSettingsOut(BaseModel):
    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    sms_enabled: bool = False
    sms_phone: Optional[str] = None
    notify_appointment_reminder: bool = True
    notify_status_change: bool = True
    notify_promo: bool = False
    remind_hours_before: int = 24

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    telegram_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    sms_phone: Optional[str] = None
    notify_appointment_reminder: Optional[bool] = None
    notify_status_change: Optional[bool] = None
    notify_promo: Optional[bool] = None
    remind_hours_before: Optional[int] = Field(None, ge=1, le=168)


class TelegramConnectRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)


# =============================================================================
# CALENDAR
# =============================================================================

class WorkingHoursOut(BaseModel):
    id: int
    master_id: int
    day_of_week: int
    start_time: str = "09:00"
    end_time: str = "18:00"
    is_working_day: bool = True

    model_config = {"from_attributes": True}


class WorkingHoursUpdate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = "09:00"
    end_time: str = "18:00"
    is_working_day: bool = True


class CalendarAppointment(BaseModel):
    id: int
    client_id: int
    master_id: Optional[int] = None
    car_id: int
    service_id: int
    start_time: str
    end_time: str
    status: str
    total_price: float = 0
    service_name: Optional[str] = None
    client_name: Optional[str] = None
    car_info: Optional[str] = None


class CalendarDay(BaseModel):
    date: str
    day_of_week: int
    appointments: list[CalendarAppointment] = []


class CalendarResponse(BaseModel):
    master_id: int
    master_name: str
    days: list[CalendarDay] = []
    working_hours: list[WorkingHoursOut] = []


# =============================================================================
# APPOINTMENT HISTORY
# =============================================================================

class HistoryEntryOut(BaseModel):
    id: int
    appointment_id: int
    change_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: list[HistoryEntryOut]
    total: int
    skip: int = 0
    limit: int = 50


# =============================================================================
# LOYALTY TIERS
# =============================================================================

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


# =============================================================================
# SERVICE ANALYTICS
# =============================================================================

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


# =============================================================================
# REPORTS
# =============================================================================

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


# =============================================================================
# PAYMENTS
# =============================================================================

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
