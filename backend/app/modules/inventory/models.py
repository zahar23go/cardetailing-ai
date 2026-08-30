"""Документы приёмки и ревизии склада."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class StockDocument(Base):
    """Приёмка (intake) или ревизия (revision) с подписью ответственного."""
    __tablename__ = "stock_documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type = Column(String(20), nullable=False, index=True)
    document_no = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    signed_name = Column(String(255), nullable=False, default="")
    signed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lines = relationship(
        "StockDocumentLine",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="StockDocumentLine.id",
    )
    signed_by = relationship("User", foreign_keys=[signed_by_id])


class StockDocumentLine(Base):
    __tablename__ = "stock_document_lines"

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("stock_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False, default="")
    unit = Column(String(20), nullable=False, default="pcs")
    system_qty = Column(Numeric(12, 3), nullable=False, default=0)
    qty = Column(Numeric(12, 3), nullable=False, default=0)
    delta = Column(Numeric(12, 3), nullable=False, default=0)

    document = relationship("StockDocument", back_populates="lines")
    material = relationship("Material")
