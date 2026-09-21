"""Pydantic schemas — модуль reviews."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    """Отзыв для добавления или импорта. Контракт для внешнего сборщика."""

    source: str = Field("manual", max_length=30)
    external_id: Optional[str] = Field(None, max_length=100)
    author: Optional[str] = Field(None, max_length=255)
    rating: Optional[int] = Field(None, ge=1, le=5)
    text: Optional[str] = None
    published_at: Optional[datetime] = None


class ReviewOut(BaseModel):
    id: int
    source: str
    external_id: Optional[str] = None
    author: Optional[str] = None
    rating: Optional[int] = None
    text: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewImportRequest(BaseModel):
    reviews: list[ReviewIn] = Field(..., min_length=1, max_length=1000)


class ReviewImportResult(BaseModel):
    imported: int
    skipped: int
    total: int


class ReviewVerdictOut(BaseModel):
    score: Optional[float] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    themes: list[dict] = []
    recommendations: list[str] = []
    reviews_count: int = 0
    average_rating: Optional[float] = None
    source: str = "ai"
    created_at: Optional[datetime] = None
