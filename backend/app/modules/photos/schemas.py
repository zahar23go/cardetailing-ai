"""Pydantic schemas — модуль photos."""
from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

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

