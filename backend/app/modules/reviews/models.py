"""SQLAlchemy models — модуль reviews."""
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Review(Base):
    """Отзыв об автомойке/детейлинг-студии: импорт или добавлен вручную."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source", "external_id",
            name="uq_reviews_tenant_source_external",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = Column(String(30), nullable=False, default="manual", comment="yandex, manual, other")
    external_id = Column(String(100), nullable=True, index=True, comment="id отзыва в источнике")
    author = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=True, comment="1..5")
    text = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", backref="reviews")


class ReviewAnalysis(Base):
    """Кэш ИИ-вердикта по качеству услуг на основе отзывов."""

    __tablename__ = "review_analyses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviews_count = Column(Integer, nullable=False, default=0)
    average_rating = Column(Float, nullable=True)
    source = Column(String(20), nullable=False, default="ai", comment="ai | heuristic")
    verdict = Column(JSONB, nullable=False, default=dict, server_default="'{}'")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant", backref="review_analyses")
