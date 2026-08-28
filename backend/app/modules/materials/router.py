"""HTTP API — модуль materials."""
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

@router.get("/api/materials/categories", response_model=list[MaterialCategoryItem])
async def get_material_categories(current_user: dict = Depends(_require_admin)):
    """Справочник категорий склада."""
    from app.services.materials_service import list_category_items
    return [MaterialCategoryItem(**c) for c in list_category_items()]

@router.get("/api/materials")
async def get_materials(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: str | None = Query(None),
    is_active: bool | None = Query(None),
    low_stock_only: bool = Query(False),
    search: str | None = Query(None, description="Поиск по name / sku / supplier"),
):
    """Список позиций склада с фильтрами."""
    from app.services.materials_service import list_materials, material_to_out
    tenant_id = UUID(current_user["tenant_id"])
    items, total = await list_materials(
        db,
        tenant_id,
        skip=skip,
        limit=limit,
        category=category,
        is_active=is_active,
        low_stock_only=low_stock_only,
        search=search,
    )
    return {
        "items": [material_to_out(m) for m in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/materials/{material_id}", response_model=MaterialOut)
async def get_material_by_id(
    material_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить позицию склада по id."""
    from app.services.materials_service import get_material, material_to_out
    material = await get_material(db, UUID(current_user["tenant_id"]), material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material_to_out(material)

@router.post("/api/materials", response_model=MaterialOut, status_code=201)
async def create_material_endpoint(
    request: MaterialCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать позицию склада."""
    from app.services.materials_service import create_material, material_to_out
    material = await create_material(db, UUID(current_user["tenant_id"]), request)
    return material_to_out(material)

@router.put("/api/materials/{material_id}", response_model=MaterialOut)
async def update_material_endpoint(
    material_id: int,
    request: MaterialUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить позицию склада."""
    from app.services.materials_service import update_material, material_to_out
    material = await update_material(
        db, UUID(current_user["tenant_id"]), material_id, request
    )
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material_to_out(material)

@router.post("/api/materials/{material_id}/adjust", response_model=MaterialOut)
async def adjust_material_quantity(
    material_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    delta: float = Query(..., description="Приход (+) или расход (−)"),
):
    """Изменить остаток: delta > 0 — приход, delta < 0 — расход (не ниже 0)."""
    from app.services.materials_service import adjust_quantity, material_to_out
    material = await adjust_quantity(
        db,
        UUID(current_user["tenant_id"]),
        material_id,
        delta,
        created_by_id=int(current_user["id"]),
    )
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material_to_out(material)

@router.delete("/api/materials/{material_id}")
async def delete_material_endpoint(
    material_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить позицию склада."""
    from app.services.materials_service import delete_material
    ok = await delete_material(db, UUID(current_user["tenant_id"]), material_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material deleted"}

