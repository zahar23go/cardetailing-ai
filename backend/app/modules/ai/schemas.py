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

