"""HTTP API — аналитика диалогов с ИИ-ассистентами (только администратор)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin as _require_admin
from app.core.database import get_db
from app.modules.ai import analytics_service

router = APIRouter(prefix="/api/ai/analytics", tags=["ai-analytics"])


@router.get("/overview")
async def chat_analytics_overview(
    period_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """KPI диалогов, динамика по дням, распределение по ассистентам, топ вопросов и функций."""
    return await analytics_service.build_overview(
        db, UUID(current_user["tenant_id"]), period_days
    )


@router.get("/dialogs")
async def chat_analytics_dialogs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Последние диалоги: ассистент, пользователь, число ходов, первая реплика."""
    return await analytics_service.list_dialogs(
        db, UUID(current_user["tenant_id"]), limit=limit, offset=offset
    )


@router.get("/dialogs/{session_id}")
async def chat_analytics_dialog(
    session_id: str,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Полная переписка одной сессии в рамках тенанта."""
    dialog = await analytics_service.get_dialog(
        db, UUID(current_user["tenant_id"]), session_id
    )
    if dialog is None:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return dialog
