"""Карточка авто: фото, характеристики, таймлайн визитов."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, Car, Photo
from app.modules.appointments.close_service import snapshot_revenue
from app.modules.cars.schemas import CarCardOut, CarVisitOut
from app.modules.photos.schemas import PhotoOut


def can_access_car(user: dict, car: Car) -> bool:
    tenant = UUID(user["tenant_id"])
    if car.tenant_id != tenant:
        return False
    role = user.get("role")
    if role in ("admin", "super_admin", "master"):
        return True
    return car.client_id == user["id"]


async def load_car(db: AsyncSession, car_id: int, tenant_id: UUID) -> Car | None:
    result = await db.execute(
        select(Car).where(Car.id == car_id, Car.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def build_car_card(db: AsyncSession, car: Car) -> CarCardOut:
    photos_result = await db.execute(
        select(Photo)
        .where(
            Photo.car_id == car.id,
            Photo.tenant_id == car.tenant_id,
            Photo.entity_type == "car",
        )
        .order_by(Photo.is_primary.desc(), Photo.sort_order, Photo.created_at.desc())
    )
    photos = [PhotoOut.model_validate(p) for p in photos_result.scalars().all()]

    appts_result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.service),
            selectinload(Appointment.master),
            selectinload(Appointment.invoice),
        )
        .where(
            Appointment.car_id == car.id,
            Appointment.tenant_id == car.tenant_id,
        )
        .order_by(Appointment.start_time.desc())
        .limit(40)
    )
    timeline: list[CarVisitOut] = []
    for a in appts_result.scalars().unique().all():
        if a.status == "cancelled":
            continue
        svc = a.service.name if a.service else ""
        master = a.master.full_name if a.master else None
        timeline.append(
            CarVisitOut(
                appointment_id=a.id,
                start_time=a.start_time,
                status=a.status,
                service_name=svc,
                master_name=master,
                price=round(snapshot_revenue(a), 2),
                notes=a.master_brief,
            )
        )

    return CarCardOut(
        id=car.id,
        client_id=car.client_id,
        make=car.make,
        model=car.model,
        year=car.year,
        license_plate=car.license_plate,
        color=car.color,
        vin=car.vin,
        body_type=car.body_type,
        mileage=car.mileage,
        notes=car.notes,
        paint_type=car.paint_type,
        glass_defects=car.glass_defects or [],
        care_requirements=car.care_requirements or [],
        condition_notes=car.condition_notes,
        created_at=car.created_at,
        photos=photos,
        timeline=timeline,
    )
