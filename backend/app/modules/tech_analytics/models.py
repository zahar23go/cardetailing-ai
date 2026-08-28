"""SQLAlchemy models — модуль tech_analytics."""
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

class AuditLogKind(str, enum.Enum):
    recommendation = "recommendation"
    audit = "audit"
    anomaly = "anomaly"

class AuditLogSeverity(str, enum.Enum):
    info = "info"
    warn = "warn"
    critical = "critical"

class AuditLog(Base):
    """
    Журнал аналитики склада: рекомендации, отклонения норма/факт, аномалии.
    Записи создаются при запуске анализа (sync) и доступны в UI «Аналитика».
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(
        String(30),
        nullable=False,
        index=True,
        comment="recommendation | audit | anomaly",
    )
    severity = Column(
        String(20),
        nullable=False,
        default=AuditLogSeverity.info.value,
        index=True,
        comment="info | warn | critical",
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=False, server_default="'{}'")
    status = Column(
        String(20),
        nullable=False,
        default="open",
        index=True,
        comment="open | resolved",
    )
    fingerprint = Column(
        String(120),
        nullable=False,
        index=True,
        comment="Дедуп-ключ: kind+material+код события",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="audit_logs")
    material = relationship("Material")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, kind={self.kind}, severity={self.severity})>"

