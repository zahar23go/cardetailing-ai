"""Pydantic schemas — модуль appointments."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

class AppointmentCreate(BaseModel):
    service_id: int
    car_id: int
    start_time: str = Field(..., description="ISO 8601 datetime string")
    notes: Optional[str] = Field(None, description="Client notes")
    client_notes: Optional[str] = None  # alias for notes
    box_id: Optional[int] = Field(None, description="ID бокса/зоны")
    master_id: Optional[int] = Field(None, description="Выбранный мастер")

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

class BoxCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    service_ids: list[int] = []

class BoxUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    service_ids: Optional[list[int]] = None

class BoxOut(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    service_ids: list[int] = []

    model_config = {"from_attributes": True}

class BoxServiceOut(BaseModel):
    id: int
    box_id: int
    service_id: int
    service_name: Optional[str] = None

    model_config = {"from_attributes": True}

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

