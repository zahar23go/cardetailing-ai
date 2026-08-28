"""HTTP API — модуль inventory."""
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

@router.get("/api/inventory/summary", response_model=InventorySummaryOut)
async def get_inventory_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сводка учёта склада."""
    from app.services.inventory_service import inventory_summary
    data = await inventory_summary(db, UUID(current_user["tenant_id"]), days=days)
    return InventorySummaryOut(**data)

@router.get("/api/inventory/movements")
async def get_inventory_movements(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    material_id: int | None = Query(None),
    movement_type: str | None = Query(None),
    days: int = Query(90, ge=1, le=365),
):
    """История движения материалов."""
    from app.services.inventory_service import list_movements, movement_to_out
    date_from = datetime.now(timezone.utc) - timedelta(days=days)
    items, total = await list_movements(
        db,
        UUID(current_user["tenant_id"]),
        skip=skip,
        limit=limit,
        material_id=material_id,
        movement_type=movement_type,
        date_from=date_from,
    )
    return {
        "items": [MaterialMovementOut(**movement_to_out(m)) for m in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/inventory/stock-history", response_model=list[StockHistoryPoint])
async def get_stock_history(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    material_id: int | None = Query(None),
    days: int = Query(30, ge=7, le=180),
):
    """График изменения остатка (по дням)."""
    from app.services.inventory_service import stock_history
    points = await stock_history(
        db,
        UUID(current_user["tenant_id"]),
        material_id=material_id,
        days=days,
    )
    return [StockHistoryPoint(**p) for p in points]

@router.get("/api/inventory/abc", response_model=list[AbcItemOut])
async def get_inventory_abc(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    days: int = Query(90, ge=7, le=365),
):
    """ABC-анализ материалов по стоимости расхода."""
    from app.services.inventory_service import abc_analysis
    rows = await abc_analysis(db, UUID(current_user["tenant_id"]), days=days)
    return [AbcItemOut(**r) for r in rows]

@router.get("/api/inventory/critical", response_model=list[CriticalItemOut])
async def get_inventory_critical(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Критические позиции (остаток ≤ мин. запас)."""
    from app.services.inventory_service import critical_positions
    rows = await critical_positions(db, UUID(current_user["tenant_id"]))
    return [CriticalItemOut(**r) for r in rows]

