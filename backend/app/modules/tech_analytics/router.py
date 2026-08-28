"""HTTP API — модуль tech_analytics."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Body, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import (
    get_current_user as _get_current_user,
    require_admin as _require_admin,
    require_master as _require_master,
    hash_password as _hash_password,
    verify_password as _verify_password,
    create_token as _create_token,
)
from app.core.endpoint_helpers import *  # noqa: F401,F403
from app.core.image_service import (
    validate_image,
    save_file_local,
    generate_filename,
    delete_file_local,
    resolve_portfolio_url,
)
from app.core.deepseek_client import get_ai_response, get_financier_response, get_consultant_response
from app.models import *  # noqa: F401,F403
from app.schemas import *  # noqa: F401,F403

router = APIRouter()

@router.get("/api/tech-analytics/summary", response_model=TechAnalyticsSummaryOut)
async def get_tech_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    cover_days: int = Query(30, ge=7, le=180),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сводка аналитики склада: закупки и аудит расхода."""
    from app.services.tech_analytics_service import tech_analytics_summary
    data = await tech_analytics_summary(
        db, UUID(current_user["tenant_id"]), days=days, cover_days=cover_days
    )
    return TechAnalyticsSummaryOut(**data)

@router.get("/api/tech-analytics/purchase-recommendations", response_model=list[PurchaseRecommendOut])
async def get_purchase_recommendations(
    days: int = Query(30, ge=7, le=365),
    cover_days: int = Query(30, ge=7, le=180),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Рекомендации по закупкам на основе расхода и мин. запаса."""
    from app.services.tech_analytics_service import purchase_recommendations
    rows = await purchase_recommendations(
        db, UUID(current_user["tenant_id"]), days=days, cover_days=cover_days
    )
    return [PurchaseRecommendOut(**r) for r in rows]

@router.get("/api/tech-analytics/consumption-audit", response_model=list[ConsumptionAuditOut])
async def get_consumption_audit(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аудит расхода: норма (техкарта × услуги) vs факт (движения)."""
    from app.services.tech_analytics_service import consumption_audit
    rows = await consumption_audit(db, UUID(current_user["tenant_id"]), days=days)
    return [ConsumptionAuditOut(**r) for r in rows]

@router.get("/api/tech-analytics/anomalies", response_model=list[AnomalyOut])
async def get_tech_anomalies(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аномалии расхода: скачки, крупные списания, перерасход, расход без нормы."""
    from app.services.tech_analytics_service import detect_anomalies
    rows = await detect_anomalies(db, UUID(current_user["tenant_id"]), days=days)
    return [AnomalyOut(**r) for r in rows]

@router.post("/api/tech-analytics/sync", response_model=AuditSyncResultOut)
async def sync_tech_analytics(
    days: int = Query(30, ge=7, le=365),
    cover_days: int = Query(30, ge=7, le=180),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Пересчитать аналитику и синхронизировать AuditLog."""
    from app.services.tech_analytics_service import sync_audit_logs
    data = await sync_audit_logs(
        db, UUID(current_user["tenant_id"]), days=days, cover_days=cover_days
    )
    return AuditSyncResultOut(**data)

@router.get("/api/tech-analytics/audit-logs")
async def get_audit_logs(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    kind: str | None = Query(None),
    status: str | None = Query("open"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Журнал AuditLog (рекомендации / аудит / аномалии)."""
    from app.services.tech_analytics_service import list_audit_logs, audit_log_to_out
    items, total = await list_audit_logs(
        db,
        UUID(current_user["tenant_id"]),
        kind=kind,
        status=status if status not in (None, "", "all") else None,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [AuditLogOut(**audit_log_to_out(i)) for i in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.post("/api/tech-analytics/audit-logs/{log_id}/resolve", response_model=AuditLogOut)
async def resolve_tech_audit_log(
    log_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Пометить запись AuditLog как resolved."""
    from app.services.tech_analytics_service import resolve_audit_log, audit_log_to_out
    row = await resolve_audit_log(db, UUID(current_user["tenant_id"]), log_id)
    if not row:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogOut(**audit_log_to_out(row))

