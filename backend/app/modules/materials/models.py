"""SQLAlchemy models — модуль materials."""
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

class MaterialCategory(str, enum.Enum):
    """Категории номенклатуры склада (модуль «Технология»)."""
    chemistry = "chemistry"          # Химия
    consumables = "consumables"      # Расходники
    inventory = "inventory"          # Инвентарь
    workwear = "workwear"            # Спецодежда
    other = "other"

class MaterialUnit(str, enum.Enum):
    """Единицы измерения на складе."""
    pcs = "pcs"   # шт
    ml = "ml"
    l = "l"
    g = "g"
    kg = "kg"
    m = "m"
    pack = "pack"  # упак.

class Material(Base):
    """
    Номенклатура склада (модуль «Технология» / Склад).

    Не путать с Service.material_cost — это скаляр себестоимости услуги в P&L.
    """
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    sku = Column(String(100), nullable=True, index=True, comment="Артикул / SKU")
    category = Column(
        String(50),
        nullable=False,
        default=MaterialCategory.other.value,
        index=True,
        comment="chemistry, consumables, inventory, workwear, other",
    )
    unit = Column(
        String(20),
        nullable=False,
        default=MaterialUnit.pcs.value,
        comment="pcs, ml, l, g, kg, m, pack",
    )
    quantity = Column(
        Numeric(12, 3),
        nullable=False,
        default=0,
        comment="Текущий остаток",
    )
    min_quantity = Column(
        Numeric(12, 3),
        nullable=False,
        default=0,
        comment="Минимальный запас (порог алерта)",
    )
    purchase_price = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Закупочная цена за единицу",
    )
    supplier = Column(String(255), nullable=True, comment="Поставщик")
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
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

    tenant = relationship("Tenant", back_populates="materials")
    tech_card_items = relationship("TechCardItem", back_populates="material")
    movements = relationship(
        "MaterialMovement",
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="MaterialMovement.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Material(id={self.id}, name='{self.name}', qty={self.quantity})>"

class MaterialMovementType(str, enum.Enum):
    """Типы движений склада."""
    in_ = "in"           # приход
    out = "out"          # расход
    adjust = "adjust"    # ручная корректировка
    initial = "initial"  # начальный остаток

class MaterialMovement(Base):
    """История движения материалов (модуль «Технология» / Учёт)."""
    __tablename__ = "material_movements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movement_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="in, out, adjust, initial",
    )
    delta = Column(
        Numeric(12, 3),
        nullable=False,
        comment="Изменение остатка (+/−)",
    )
    quantity_before = Column(Numeric(12, 3), nullable=False, default=0)
    quantity_after = Column(Numeric(12, 3), nullable=False, default=0)
    reason = Column(String(255), nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    material = relationship("Material", back_populates="movements")
    created_by = relationship("User")

    def __repr__(self) -> str:
        return f"<MaterialMovement(id={self.id}, material={self.material_id}, delta={self.delta})>"

