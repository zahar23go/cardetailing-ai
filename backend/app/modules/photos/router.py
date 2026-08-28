"""HTTP API — модуль photos."""
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

@router.post("/api/upload/car/{car_id}", response_model=PhotoCreateResponse)
async def upload_car_photo(
    car_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото автомобиля."""
    result = await db.execute(
        select(Car).where(Car.id == car_id, Car.client_id == current_user["id"],
                          Car.tenant_id == UUID(current_user["tenant_id"]))
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "car", "car_id", car_id,
        current_user["id"],
    )

@router.post("/api/upload/appointment/{appointment_id}", response_model=PhotoCreateResponse)
async def upload_appointment_photo(
    appointment_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото выполненной работы (до/после)."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appt.client_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "appointment", "appointment_id", appointment_id,
        current_user["id"],
    )

@router.post("/api/upload/portfolio", response_model=PhotoCreateResponse)
async def upload_portfolio_photo(
    file: UploadFile = File(...),
    title: str | None = Query(None),
    service_id: int | None = Query(None, description="ID услуги, к которой относится фото"),
    description: str | None = Query(None, description="Описание работы (было → стало)"),
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото в портфолио мастера с привязкой к услуге."""
    # Если указан service_id — проверяем, что услуга существует
    if service_id is not None:
        srv_result = await db.execute(
            select(Service).where(
                Service.id == service_id,
                Service.tenant_id == UUID(current_user["tenant_id"]),
            )
        )
        if not srv_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Услуга не найдена")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "portfolio", "uploaded_by_id", current_user["id"],
        current_user["id"], title=title, service_id=service_id, description=description,
    )

@router.get("/api/photos/{entity_type}/{entity_id}", response_model=list[PhotoOut])
async def get_photos(
    entity_type: str,
    entity_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список фото для сущности."""
    entity_field = {
        "car": "car_id",
        "appointment": "appointment_id",
        "portfolio": "uploaded_by_id",
    }.get(entity_type, "car_id")

    filter_col = getattr(Photo, entity_field, None)
    if filter_col is None:
        raise HTTPException(status_code=400, detail="Некорректный тип сущности")

    # Для портфолио подгружаем связи с услугой и загрузчиком
    query = select(Photo).where(
        filter_col == entity_id,
        Photo.tenant_id == UUID(current_user["tenant_id"]),
        Photo.entity_type == entity_type,
    )
    if entity_type == "portfolio":
        query = query.options(
            selectinload(Photo.service),
            selectinload(Photo.uploader),
        )
    result = await db.execute(query.order_by(Photo.sort_order, Photo.created_at.desc()))
    photos = result.scalars().all()

    # Обогащаем ответ именами для портфолио
    result_list = []
    for p in photos:
        po = PhotoOut.model_validate(p)
        if entity_type == "portfolio":
            po.service_name = p.service.name if p.service else None
            po.uploader_name = p.uploader.full_name if p.uploader else None
            hay = f"{po.service_name or ''} {p.title or ''}"
            po.url = resolve_portfolio_url(p.url, hay)
            po.thumbnail_url = resolve_portfolio_url(p.thumbnail_url or p.url, hay)
        result_list.append(po)
    return result_list

@router.get("/api/portfolio", response_model=list[PhotoOut])
async def get_all_portfolio(
    service_id: int | None = Query(None, description="Фильтр по услуге"),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить все портфолио-фото салона (с фильтром по услуге)."""
    tenant_id = UUID(current_user["tenant_id"])
    query = (
        select(Photo)
        .options(selectinload(Photo.service), selectinload(Photo.uploader))
        .where(
            Photo.tenant_id == tenant_id,
            Photo.entity_type == "portfolio",
        )
    )
    if service_id is not None:
        query = query.where(Photo.service_id == service_id)

    result = await db.execute(query.order_by(Photo.created_at.desc()))
    photos = result.scalars().all()

    result_list = []
    for p in photos:
        po = PhotoOut.model_validate(p)
        po.service_name = p.service.name if p.service else None
        po.uploader_name = p.uploader.full_name if p.uploader else None
        hay = f"{po.service_name or ''} {p.title or ''}"
        po.url = resolve_portfolio_url(p.url, hay)
        po.thumbnail_url = resolve_portfolio_url(p.thumbnail_url or p.url, hay)
        result_list.append(po)
    return result_list

@router.get("/api/portfolio/services", response_model=list[dict])
async def get_portfolio_services(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список услуг, по которым есть фото в портфолио."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Photo.service_id, func.count(Photo.id).label("photo_count"))
        .where(
            Photo.tenant_id == tenant_id,
            Photo.entity_type == "portfolio",
            Photo.service_id.isnot(None),
        )
        .group_by(Photo.service_id)
        .order_by(func.count(Photo.id).desc())
    )
    rows = result.all()
    service_ids = [r.service_id for r in rows if r.service_id]

    services_out = []
    if service_ids:
        srv_result = await db.execute(
            select(Service).where(Service.id.in_(service_ids))
        )
        srv_map = {s.id: s for s in srv_result.scalars().all()}
        for r in rows:
            srv = srv_map.get(r.service_id)
            services_out.append({
                "service_id": r.service_id,
                "service_name": srv.name if srv else f"Услуга #{r.service_id}",
                "photo_count": r.photo_count,
            })
    return services_out

@router.delete("/api/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить фото."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    delete_file_local(photo.url)
    if photo.thumbnail_url:
        delete_file_local(photo.thumbnail_url)

    await db.delete(photo)
    await db.commit()
    return {"message": "Фото удалено", "photo_id": photo_id}

@router.put("/api/photos/{photo_id}/primary")
async def set_primary_photo(
    photo_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Сделать фото основным."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    photo.is_primary = True
    await db.commit()
    return {"message": "Фото отмечено как основное", "photo_id": photo_id}

@router.put("/api/photos/{photo_id}/order")
async def update_photo_order(
    photo_id: int,
    request: PhotoOrderUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Изменить порядок фото."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    photo.sort_order = request.sort_order
    await db.commit()
    return {"message": "Порядок фото обновлён", "photo_id": photo_id}

