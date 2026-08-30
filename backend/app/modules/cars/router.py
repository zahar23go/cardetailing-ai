"""HTTP API — модуль cars."""
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

@router.get("/api/cars")
async def get_cars(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить все машины текущего пользователя"""
    stmt = (
        select(Car)
        .where(
            Car.client_id == current_user["id"],
            Car.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Car.created_at.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[CarOut](
        items=[CarOut.model_validate(c) for c in items],
        total=total, skip=skip, limit=limit,
    )

@router.post("/api/cars", response_model=CarOut)
async def create_car(
    car_data: CarCreate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую машину для текущего пользователя"""
    new_car = Car(
        client_id=current_user["id"],
        make=car_data.make,
        model=car_data.model,
        year=car_data.year,
        license_plate=car_data.license_plate,
        color=car_data.color,
        vin=car_data.vin,
        body_type=car_data.body_type,
        mileage=car_data.mileage,
        notes=car_data.notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(new_car)
    await db.commit()
    await db.refresh(new_car)
    return CarOut.model_validate(new_car)


@router.get("/api/cars/{car_id}", response_model=CarCardOut)
async def get_car_card(
    car_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Карточка авто: фото, VIN, характеристики, таймлайн визитов."""
    from app.modules.cars.card_service import build_car_card, can_access_car, load_car

    car = await load_car(db, car_id, UUID(current_user["tenant_id"]))
    if not car or not can_access_car(current_user, car):
        raise HTTPException(status_code=404, detail="Машина не найдена")
    return await build_car_card(db, car)


@router.put("/api/cars/{car_id}", response_model=CarOut)
async def update_car(
    car_id: int,
    car_data: CarUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить свой автомобиль."""
    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.client_id == current_user["id"],
            Car.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    update_data = car_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(car, key, value)
    await db.commit()
    await db.refresh(car)
    return CarOut.model_validate(car)

@router.delete("/api/cars/{car_id}")
async def delete_car(
    car_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить машину (только свою)"""
    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.client_id == current_user["id"],
            Car.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    
    await db.delete(car)
    await db.commit()
    return {"message": "Машина удалена"}

