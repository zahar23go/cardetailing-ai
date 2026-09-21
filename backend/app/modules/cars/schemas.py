"""Pydantic schemas — модуль cars."""
from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator

from app.modules.photos.schemas import PhotoOut

_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{11,17}$")


def _normalize_vin(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"[\s-]+", "", value).upper()
    if not cleaned:
        return None
    if not _VIN_RE.match(cleaned):
        raise ValueError("VIN: 11–17 символов, без I, O, Q")
    return cleaned


class CarCreate(BaseModel):
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1990, le=2030)
    license_plate: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=30)
    vin: Optional[str] = Field(None, max_length=17)
    body_type: Optional[str] = Field(None, max_length=40)
    mileage: Optional[int] = Field(None, ge=0, le=2_000_000)
    notes: Optional[str] = None

    @field_validator("vin")
    @classmethod
    def validate_vin(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_vin(v)


class CarOut(BaseModel):
    id: int
    client_id: int
    make: str
    model: str
    year: Optional[int] = None
    license_plate: Optional[str] = None
    color: Optional[str] = None
    vin: Optional[str] = None
    body_type: Optional[str] = None
    mileage: Optional[int] = None
    notes: Optional[str] = None
    paint_type: Optional[str] = None
    glass_defects: list[str] = []
    care_requirements: list[str] = []
    condition_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CarUpdate(BaseModel):
    make: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1990, le=2030)
    license_plate: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=30)
    vin: Optional[str] = Field(None, max_length=17)
    body_type: Optional[str] = Field(None, max_length=40)
    mileage: Optional[int] = Field(None, ge=0, le=2_000_000)
    notes: Optional[str] = None

    @field_validator("vin")
    @classmethod
    def validate_vin(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_vin(v)


class CarVisitOut(BaseModel):
    appointment_id: int
    start_time: datetime
    status: str
    service_name: str = ""
    master_name: Optional[str] = None
    price: float = 0
    notes: Optional[str] = None


class CarCardOut(CarOut):
    photos: list[PhotoOut] = []
    timeline: list[CarVisitOut] = []


class CarCondition(BaseModel):
    """Состояние авто: тип краски, дефекты стекла, требования + комментарий."""

    paint_type: Optional[str] = None
    glass_defects: list[str] = []
    care_requirements: list[str] = []
    notes: Optional[str] = None


class ConditionCatalogItem(BaseModel):
    id: str
    label: str


class ConditionCatalogOut(BaseModel):
    paint_types: list[ConditionCatalogItem]
    glass_defects: list[ConditionCatalogItem]
    care_requirements: list[ConditionCatalogItem]
