"""Pydantic schemas — модуль core."""
import re
from datetime import datetime
from decimal import Decimal
from typing import Generic, Literal, Optional, TypeVar
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
    consent: bool = Field(..., description="Согласие на обработку персональных данных (152-ФЗ)")
    consent_version: Optional[str] = Field(None, max_length=20)

    @field_validator("consent")
    @classmethod
    def _consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Требуется согласие на обработку персональных данных")
        return value


_ACCENT_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_RADIUS_RE = re.compile(r"^(?:[0-9]|[12][0-9]|3[0-2])px$")
_FONT_RE = re.compile(r"^[A-Za-z0-9 ,'\"\-]{1,120}$")
_LOGO_PREFIXES = ("/uploads/", "/icons/", "http://", "https://")


class BrandingUpdate(BaseModel):
    """White Label салона: сохраняется в tenant.config.branding."""

    accent_solid: Optional[str] = Field(None, description="Hex-цвет акцента, #RRGGBB")
    radius_md: Optional[str] = Field(None, description="Скругление, например 14px")
    font_ui: Optional[str] = Field(None, max_length=120, description="CSS font-family")
    base_theme: Optional[Literal["goldMetal", "goldGlow", "silver"]] = None
    surface_mode: Optional[Literal["light", "dark"]] = None
    logo_url: Optional[str] = Field(None, max_length=500)

    @field_validator("accent_solid")
    @classmethod
    def _accent(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not _ACCENT_RE.fullmatch(value):
            raise ValueError("accent_solid должен быть в формате #RRGGBB")
        return value.upper()

    @field_validator("radius_md")
    @classmethod
    def _radius(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not _RADIUS_RE.fullmatch(value):
            raise ValueError("radius_md должен быть в формате 0px…32px")
        return value

    @field_validator("font_ui")
    @classmethod
    def _font(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not _FONT_RE.fullmatch(value):
            raise ValueError("font_ui содержит недопустимые символы")
        return value

    @field_validator("logo_url")
    @classmethod
    def _logo(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith(_LOGO_PREFIXES):
            raise ValueError("logo_url должен начинаться с /uploads/, /icons/ или http(s)://")
        return value

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
    branding: dict = Field(default_factory=dict)


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

