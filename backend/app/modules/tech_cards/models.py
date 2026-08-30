"""SQLAlchemy models — модуль tech_cards."""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.core.database import Base

class TechCard(Base):
    """
    Техкарта: пошаговая инструкция услуги (блоки) + расход материалов.
    Одна техкарта на услугу в рамках тенанта.
    """
    __tablename__ = "tech_cards"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service_id", name="uq_tech_cards_tenant_service"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id = Column(
        Integer,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=True, comment="Название техкарты (по умолчанию — имя услуги)")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    current_version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="tech_cards")
    service = relationship("Service")
    blocks = relationship(
        "TechCardBlock",
        back_populates="tech_card",
        cascade="all, delete-orphan",
        order_by="TechCardBlock.sort_order",
    )
    items = relationship(
        "TechCardItem",
        back_populates="tech_card",
        order_by="TechCardItem.id",
        viewonly=True,
    )
    versions = relationship(
        "TechCardVersion",
        back_populates="tech_card",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<TechCard(id={self.id}, service_id={self.service_id})>"

class TechCardBlock(Base):
    """Шаг техкарты: название, инструкция, длительность, фото, материалы."""
    __tablename__ = "tech_card_blocks"

    id = Column(Integer, primary_key=True, index=True)
    tech_card_id = Column(
        Integer,
        ForeignKey("tech_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=0)
    photo_url = Column(Text, nullable=True)

    tech_card = relationship("TechCard", back_populates="blocks")
    items = relationship(
        "TechCardItem",
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="TechCardItem.id",
    )

    def __repr__(self) -> str:
        return f"<TechCardBlock(id={self.id}, card={self.tech_card_id}, title={self.title!r})>"

class TechCardItem(Base):
    """Строка техкарты: материал и расход на шаг / услугу."""
    __tablename__ = "tech_card_items"
    __table_args__ = (
        UniqueConstraint("block_id", "material_id", name="uq_tech_card_items_block_material"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tech_card_id = Column(
        Integer,
        ForeignKey("tech_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id = Column(
        Integer,
        ForeignKey("tech_card_blocks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity = Column(
        Numeric(12, 3),
        nullable=False,
        default=0,
        comment="Расход материала на одну услугу / шаг",
    )
    notes = Column(Text, nullable=True)

    tech_card = relationship("TechCard", back_populates="items", viewonly=True)
    block = relationship("TechCardBlock", back_populates="items")
    material = relationship("Material", back_populates="tech_card_items")

    def __repr__(self) -> str:
        return f"<TechCardItem(card={self.tech_card_id}, material={self.material_id}, qty={self.quantity})>"


class TechCardVersion(Base):
    """Снимок техкарты: какая норма и инструкция действовали."""
    __tablename__ = "tech_card_versions"
    __table_args__ = (
        UniqueConstraint("tech_card_id", "version_no", name="uq_tech_card_versions_card_no"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tech_card_id = Column(
        Integer,
        ForeignKey("tech_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False, default=dict)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tech_card = relationship("TechCard", back_populates="versions")

