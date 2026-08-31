"""Pydantic schemas — модуль core."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

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
    plan: Optional[str] = "business"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

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
    enabled_modules: list[str] = Field(default_factory=list)
    plan: Optional[str] = None
    plan_label: Optional[str] = None
    price: Optional[int] = None
    appointment_limit: Optional[int] = None
    appointments_this_month: Optional[int] = None
    features: dict[str, bool] = Field(default_factory=dict)
    tenant_name: Optional[str] = None
    logo_url: Optional[str] = None
    pwa: dict = Field(default_factory=dict)


class PlanCatalogItem(BaseModel):
    id: str
    label: str
    price: int
    appointment_limit: Optional[int] = None
    modules: list[str] = []
    features: dict[str, bool] = {}
    blurb: str = ""


class TenantPlanUpdate(BaseModel):
    plan: str = Field(..., min_length=3, max_length=20)

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    phone: Optional[str] = Field(None, min_length=1, max_length=20)

class UserListOut(BaseModel):
    id: int
    phone: str
    full_name: str
    role: str
    commission_percent: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("commission_percent", mode="before")
    @classmethod
    def _commission(cls, v):
        if v is None or v == "":
            return 0
        return v

class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="New role: client, master, admin, super_admin")


class UserCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=4, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=150)
    role: str = Field(default="master")


class OnboardingStatus(BaseModel):
    completed: bool = False
    needs_wizard: bool = False
    salon_name: str = ""
    boxes: int = 0
    services: int = 0
    masters: int = 0
    materials: int = 0

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

