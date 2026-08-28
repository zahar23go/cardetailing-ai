"""HTTP API — модуль services."""
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

@router.get("/api/services")
async def get_services(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Service)
        .where(
            Service.is_active == True,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Service.name)
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[ServiceOut](
        items=[_service_to_out(s) for s in items],
        total=total, skip=skip, limit=limit,
    )

@router.post("/api/services", response_model=ServiceOut)
async def create_service(
    request: ServiceCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    cost = request.cost_price if request.cost_price is not None else 0
    if cost <= 0:
        cost = request.material_cost or 0
    service = Service(
        name=request.name,
        description=request.description,
        category=request.category,
        price=request.price,
        duration=request.duration,
        material_cost=request.material_cost,
        cost_price=cost,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return _service_to_out(service)

@router.put("/api/services/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: int,
    request: ServiceUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)
    return _service_to_out(service)

@router.delete("/api/services/{service_id}")
async def delete_service(
    service_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    # Проверяем, есть ли связанные записи
    appt_result = await db.execute(
        select(Appointment).where(Appointment.service_id == service_id)
    )
    related_appts = appt_result.scalars().all()
    if related_appts:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя удалить услугу «{service.name}»: есть {len(related_appts)} связанн{'ая' if len(related_appts) == 1 else 'ые'} запис{'ь' if len(related_appts) == 1 else 'и'}. "
                   f"Сначала удалите или переназначьте записи.",
        )

    await db.delete(service)
    await db.commit()
    return {"message": f"Услуга «{service.name}» удалена"}

