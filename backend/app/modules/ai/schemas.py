"""Pydantic schemas — модуль ai."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    response: str

class FinancierRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class FinancierResponse(BaseModel):
    response: str


class FinancierWeatherDayOut(BaseModel):
    date: str
    t_max: float
    t_min: float
    precip_mm: float


class FinancierRecOut(BaseModel):
    id: str
    cause: str
    action: str
    effect_rub: int
    horizon: str
    kind: str


class FinancierBriefResponse(BaseModel):
    city: str
    source: str
    season: str
    season_label: str
    season_demand: str
    outlook: str
    days: list[FinancierWeatherDayOut] = []
    recommendations: list[FinancierRecOut] = []
    month_revenue: float = 0
    net_profit: float = 0
    avg_check: float = 0


class DetailerInspectRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=2000)
    car_id: Optional[int] = None
    service_id: Optional[int] = None
    photo_ids: list[int] = Field(default_factory=list)
    tz_offset: int = Field(0, ge=-840, le=840, description="Минуты к востоку от UTC")


class DetailerFindingOut(BaseModel):
    tag: str
    area: str
    title: str
    detail: str


class DetailerOfferOut(BaseModel):
    service_id: int
    name: str
    price: float
    duration: int
    category: Optional[str] = None
    reason: Optional[str] = None


class DetailerSlotOut(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    label: Optional[str] = None
    time: Optional[str] = None
    date: Optional[str] = None
    box_id: Optional[int] = None
    box_name: Optional[str] = None
    free_boxes: int = 0
    duration: Optional[int] = None
    available: Optional[bool] = None


class DetailerInspectResponse(BaseModel):
    id: int
    tags: list[str] = []
    findings: list[DetailerFindingOut] = []
    primary: Optional[DetailerOfferOut] = None
    upsells: list[DetailerOfferOut] = []
    slots: list[DetailerSlotOut] = []
    master_brief: str = ""
    photo_count: int = 0


class DetailerTagOut(BaseModel):
    id: str
    label: str
    area: str


class DetailerSlotsResponse(BaseModel):
    items: list[DetailerSlotOut]
    date: Optional[str] = None


class DetailerBriefResponse(BaseModel):
    appointment_id: int
    inspect_id: Optional[int] = None
    master_brief: Optional[str] = None
    findings: list[DetailerFindingOut] = []
    upsells: list[DetailerOfferOut] = []
    photo_count: int = 0

