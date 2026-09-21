"""HTTP API — модуль appointments."""
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

@router.get("/api/masters")
async def list_masters(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    service_id: int | None = Query(None, description="Только мастера этой услуги (без навыков = все)"),
):
    """Список мастеров салона для записи клиента."""
    from app.modules.appointments.skills import eligible_master_ids

    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(User)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.master.value,
        )
        .order_by(User.full_name)
    )
    masters = list(result.scalars().all())
    if service_id:
        allowed = await eligible_master_ids(
            db, tenant_id, service_id, [u.id for u in masters],
        )
        masters = [u for u in masters if u.id in allowed]
    return {
        "items": [{"id": u.id, "full_name": u.full_name} for u in masters],
        "total": len(masters),
    }


@router.get("/api/masters/{master_id}/skills")
async def get_master_skills(
    master_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.appointments.skills import get_master_or_404, list_skills, tech_card_service_ids

    tenant_id = UUID(current_user["tenant_id"])
    master = await get_master_or_404(db, tenant_id, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    skills = await list_skills(db, tenant_id, master_id)
    has_cards = await tech_card_service_ids(db, tenant_id, [s.service_id for s in skills])
    return {
        "master_id": master.id,
        "full_name": master.full_name,
        "commission_percent": int(master.commission_percent or 0),
        "items": [
            {
                "service_id": s.service_id,
                "service_name": s.service.name if s.service else "",
                "has_tech_card": s.service_id in has_cards,
                "commission_percent": int(s.commission_percent or 0),
            }
            for s in skills
        ],
    }


@router.put("/api/masters/{master_id}/skills")
async def put_master_skills(
    master_id: int,
    request: MasterSkillsPut,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.appointments.skills import clamp_percent, get_master_or_404, list_skills, tech_card_service_ids

    tenant_id = UUID(current_user["tenant_id"])
    master = await get_master_or_404(db, tenant_id, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    default_pct = clamp_percent(request.commission_percent)
    master.commission_percent = default_pct

    service_ids = [it.service_id for it in request.items]
    if service_ids:
        svc_result = await db.execute(
            select(Service.id).where(
                Service.tenant_id == tenant_id,
                Service.id.in_(service_ids),
            )
        )
        found = {row[0] for row in svc_result.all()}
        missing = [sid for sid in service_ids if sid not in found]
        if missing:
            raise HTTPException(status_code=404, detail="Услуга не найдена")

    await db.execute(
        delete(MasterSkill).where(
            MasterSkill.tenant_id == tenant_id,
            MasterSkill.master_id == master_id,
        )
    )
    seen: set[int] = set()
    for it in request.items:
        if it.service_id in seen:
            continue
        seen.add(it.service_id)
        pct = clamp_percent(it.commission_percent if it.commission_percent is not None else default_pct)
        db.add(MasterSkill(
            tenant_id=tenant_id,
            master_id=master_id,
            service_id=it.service_id,
            commission_percent=pct,
        ))
    await db.commit()

    skills = await list_skills(db, tenant_id, master_id)
    has_cards = await tech_card_service_ids(db, tenant_id, [s.service_id for s in skills])
    return {
        "master_id": master.id,
        "full_name": master.full_name,
        "commission_percent": int(master.commission_percent or 0),
        "items": [
            {
                "service_id": s.service_id,
                "service_name": s.service.name if s.service else "",
                "has_tech_card": s.service_id in has_cards,
                "commission_percent": int(s.commission_percent or 0),
            }
            for s in skills
        ],
    }

@router.get("/api/appointments")
async def get_all_appointments(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(Appointment.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/appointments/me")
async def get_my_appointments(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(
            Appointment.client_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.car),
            selectinload(Appointment.master),
        )
        .where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.client_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return _serialize_appointment(appointment)

@router.post("/api/appointments", response_model=AppointmentOut)
async def create_appointment(
    request: AppointmentCreate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Проверка услуги
    result = await db.execute(select(Service).where(Service.id == request.service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Проверка машины
    result = await db.execute(select(Car).where(Car.id == request.car_id, Car.client_id == current_user["id"]))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    start_time = datetime.fromisoformat(request.start_time)
    # Приводим к timezone-aware (UTC), т.к. колонки DateTime(timezone=True)
    if start_time.tzinfo is None:
        # Если часовой пояс не указан — считаем, что время уже в UTC
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        # Если часовой пояс указан — конвертируем в UTC
        start_time = start_time.astimezone(timezone.utc)

    end_time = start_time + timedelta(minutes=service.duration)

    tenant_id = UUID(current_user["tenant_id"])
    from app.modules.plans import ensure_appointment_quota
    await ensure_appointment_quota(db, tenant_id, start_time)

    inspect_row = None
    master_brief = None
    if request.inspect_id:
        insp_result = await db.execute(
            select(DetailerInspection).where(
                DetailerInspection.id == request.inspect_id,
                DetailerInspection.tenant_id == tenant_id,
                DetailerInspection.client_id == current_user["id"],
            )
        )
        inspect_row = insp_result.scalar_one_or_none()
        if not inspect_row:
            raise HTTPException(status_code=404, detail="Осмотр не найден")
        master_brief = inspect_row.master_brief

    # Авто-назначение бокса по услуге, если не указан
    box_id = request.box_id
    if box_id is None and inspect_row is not None and inspect_row.suggested_box_id:
        box_id = inspect_row.suggested_box_id
    if box_id is None:
        bs_result = await db.execute(
            select(BoxService).where(
                BoxService.service_id == request.service_id,
                BoxService.tenant_id == tenant_id,
            ).limit(1)
        )
        bs = bs_result.scalar_one_or_none()
        if bs:
            box_id = bs.box_id

    master_id = request.master_id
    if master_id is not None:
        master_result = await db.execute(
            select(User).where(
                User.id == master_id,
                User.tenant_id == tenant_id,
                User.role == UserRole.master.value,
            )
        )
        if not master_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Мастер не найден")
        from app.modules.appointments.skills import master_can_do
        if not await master_can_do(db, tenant_id, master_id, request.service_id):
            raise HTTPException(status_code=400, detail="Этот мастер не выполняет выбранную услугу")

    appointment = Appointment(
        client_id=current_user["id"],
        service_id=request.service_id,
        car_id=request.car_id,
        master_id=master_id,
        start_time=start_time,
        end_time=end_time,
        total_price=service.price,
        status="pending",
        client_notes=request.notes or request.client_notes,
        master_brief=master_brief,
        box_id=box_id,
        tenant_id=tenant_id,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    if inspect_row is not None:
        inspect_row.appointment_id = appointment.id
        photo_ids = list(inspect_row.photo_ids or [])
        if photo_ids:
            await db.execute(
                update(Photo)
                .where(
                    Photo.id.in_(photo_ids),
                    Photo.tenant_id == tenant_id,
                )
                .values(appointment_id=appointment.id)
            )
        await db.commit()

    # Автоматическое применение скидок
    await _auto_apply_discount(appointment.id, db)

    # Перезагружаем запись после применения скидки
    await db.refresh(appointment)

    # Загружаем связи, чтобы не упасть с MissingGreenlet
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment.id)
        .options(selectinload(Appointment.client), selectinload(Appointment.service), selectinload(Appointment.car), selectinload(Appointment.master))
    )
    
    loaded = result.scalar_one()
    # History: log creation
    from app.services.history_service import log_create as _log_create
    await _log_create(db, loaded, current_user["id"])

    return _serialize_appointment(loaded)

@router.put("/api/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: int,
    request: AppointmentStatusUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Capture old data for history
    old_data = {
        "status": appointment.status,
        "master_id": appointment.master_id,
        "master_brief": appointment.master_brief,
    }
    if request.status is not None:
        appointment.status = request.status
    if request.master_id is not None:
        from app.modules.appointments.skills import master_can_do
        if not await master_can_do(
            db,
            UUID(current_user["tenant_id"]),
            request.master_id,
            appointment.service_id,
        ):
            raise HTTPException(status_code=400, detail="Этот мастер не выполняет услугу этой записи")
        appointment.master_id = request.master_id
    if request.master_brief is not None:
        appointment.master_brief = request.master_brief

    if request.status == "completed" and old_data["status"] != "completed":
        from app.modules.appointments.close_service import ensure_invoice
        await ensure_invoice(
            db,
            appointment,
            UUID(current_user["tenant_id"]),
            user_id=current_user["id"],
        )

    await db.commit()

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one()

    # Начисляем баллы, если статус стал completed
    if request.status == "completed":
        await _award_loyalty_points(appointment.id, db)

    return _serialize_appointment(appointment)

@router.get("/api/appointments/{appointment_id}/close-preview")
async def get_appointment_close_preview(
    appointment_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Превью закрытия заезда: шаги техкарты, норма/факт, оценка себестоимости."""
    from app.modules.appointments.close_service import preview_close

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return await preview_close(db, appointment, UUID(current_user["tenant_id"]))


@router.post("/api/appointments/{appointment_id}/close")
async def close_appointment(
    appointment_id: int,
    request: AppointmentCloseRequest = AppointmentCloseRequest(),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Закрыть заезд: чек, списание склада, статус completed. Повтор безопасен."""
    from app.modules.appointments.close_service import ensure_invoice, serialize_invoice

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status in ("cancelled", "no_show"):
        raise HTTPException(status_code=400, detail="Нельзя закрыть отменённую запись")

    body = request
    became_completed = appointment.status != "completed"
    if became_completed:
        appointment.status = "completed"
    inv = await ensure_invoice(
        db,
        appointment,
        UUID(current_user["tenant_id"]),
        user_id=current_user["id"],
        steps_in=[s.model_dump() for s in body.steps],
        materials_in=[m.model_dump() for m in body.materials],
        actual_time=body.actual_time,
        notes=body.notes,
    )
    await db.commit()
    if became_completed:
        await _award_loyalty_points(appointment.id, db)
    return serialize_invoice(inv)


@router.put("/api/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отменить запись (только свою, только в статусах pending/confirmed)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.client_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    if appointment.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя отменить запись в статусе «{appointment.status}». "
                   f"Допустимо только для «Ожидает» или «Подтверждена».",
        )

    appointment.status = "cancelled"
    await db.commit()

    # Перезагружаем со связями, чтобы избежать MissingGreenlet
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
        )
    )
    appointment = result.scalar_one()

    # History: log cancel
    from app.services.history_service import log_cancel as _log_cancel
    await _log_cancel(db, appointment, current_user["id"])
    return _serialize_appointment(appointment)

@router.put("/api/appointments/{appointment_id}/edit")
async def edit_appointment(
    appointment_id: int,
    request: ClientAppointmentEdit,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Редактировать запись (только свою, только в статусах pending/confirmed)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.client_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    if appointment.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя редактировать запись в статусе «{appointment.status}».",
        )

    # Update fields if provided
    if request.start_time is not None:
        start_time = datetime.fromisoformat(request.start_time)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        appointment.start_time = start_time
        # Recalculate end_time based on service duration
        appointment.end_time = start_time + timedelta(minutes=appointment.service.duration)

    if request.car_id is not None:
        # Verify car belongs to user
        car_result = await db.execute(
            select(Car).where(Car.id == request.car_id, Car.client_id == current_user["id"])
        )
        car = car_result.scalar_one_or_none()
        if not car:
            raise HTTPException(status_code=404, detail="Автомобиль не найден")
        appointment.car_id = request.car_id

    if request.client_notes is not None:
        appointment.client_notes = request.client_notes

    await db.commit()
    # Reload with relationships for serialization
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(*_APPT_LOAD)
    )
    return _serialize_appointment(result.scalar_one())

@router.get("/api/masters/me/appointments")
async def get_my_master_appointments(
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить записи, назначенные текущему мастеру."""
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(
            Appointment.master_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
            Appointment.status.in_(["pending", "confirmed", "in_progress"]),
        )
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/api/masters/me/kpi", response_model=MasterKpiOut)
async def get_my_master_kpi(
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Личные KPI мастера за месяц: выручка, повтор, техкарта, перерасход, оценка смены."""
    from app.modules.appointments.kpi_service import build_master_kpi

    return await build_master_kpi(
        db,
        UUID(current_user["tenant_id"]),
        current_user["id"],
    )


@router.put("/api/masters/me/appointments/{appointment_id}/status")
async def update_master_appointment_status(
    appointment_id: int,
    request: MasterStatusUpdate,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Сменить статус записи (master: in_progress → completed или confirmed → in_progress)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    new_status = request.status
    # Разрешённые переходы для мастера
    valid_transitions = {
        "confirmed": ["in_progress"],
        "in_progress": ["completed"],
    }
    allowed = valid_transitions.get(appointment.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя сменить статус с '{appointment.status}' на '{new_status}'. "
                   f"Допустимо: {allowed}",
        )

    appointment.status = new_status

    if new_status == "completed":
        from app.modules.appointments.close_service import ensure_invoice
        await ensure_invoice(
            db,
            appointment,
            UUID(current_user["tenant_id"]),
            user_id=current_user["id"],
        )

    await db.commit()

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one()

    # History: log status change
    from app.services.history_service import log_status_change as _log_sc
    await _log_sc(db, appointment.id, appointment.status, new_status, current_user["id"])

    # Начисляем баллы, если мастер завершил запись
    if new_status == "completed":
        await _award_loyalty_points(appointment.id, db)

    return _serialize_appointment(appointment)

@router.get("/api/masters/me/appointments/{appointment_id}/close-preview")
async def get_master_appointment_close_preview(
    appointment_id: int,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Превью закрытия заезда для мастера."""
    from app.modules.appointments.close_service import preview_close

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")
    return await preview_close(db, appointment, UUID(current_user["tenant_id"]))


@router.post("/api/masters/me/appointments/{appointment_id}/close")
async def close_master_appointment(
    appointment_id: int,
    request: AppointmentCloseRequest = AppointmentCloseRequest(),
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Мастер закрывает заезд: чек-лист, списание, completed. Повтор безопасен."""
    from app.modules.appointments.close_service import ensure_invoice, serialize_invoice

    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    if appointment.status == "completed":
        inv = await ensure_invoice(
            db,
            appointment,
            UUID(current_user["tenant_id"]),
            user_id=current_user["id"],
        )
        return serialize_invoice(inv)

    if appointment.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя закрыть запись в статусе '{appointment.status}'. Сначала возьмите в работу.",
        )

    body = request
    appointment.status = "completed"
    inv = await ensure_invoice(
        db,
        appointment,
        UUID(current_user["tenant_id"]),
        user_id=current_user["id"],
        steps_in=[s.model_dump() for s in body.steps],
        materials_in=[m.model_dump() for m in body.materials],
        notes=body.notes,
    )
    await db.commit()

    from app.services.history_service import log_status_change as _log_sc
    await _log_sc(db, appointment.id, "in_progress", "completed", current_user["id"])
    await _award_loyalty_points(appointment.id, db)
    return serialize_invoice(inv)

@router.put("/api/masters/me/appointments/{appointment_id}/notes")
async def update_master_appointment_notes(
    appointment_id: int,
    request: MasterNotesUpdate,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Добавить/обновить заметку мастера по записи."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    appointment.master_brief = request.master_brief
    await db.commit()
    return _serialize_appointment(appointment)


@router.put("/api/appointments/{appointment_id}/car-condition", response_model=AppointmentOut)
async def set_appointment_car_condition(
    appointment_id: int,
    condition: CarCondition,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Снимок состояния авто на визит — владелец записи или сотрудник."""
    from app.modules.cars.condition import clean_condition

    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == tenant_id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    is_staff = current_user["role"] in ("admin", "super_admin", "master")
    if appointment.client_id != current_user["id"] and not is_staff:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    appointment.car_condition = clean_condition(
        condition.paint_type,
        condition.glass_defects,
        condition.care_requirements,
        condition.notes,
    )
    await db.commit()

    refreshed = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    return _serialize_appointment(refreshed.scalar_one())


@router.get("/api/masters/me/appointments/{appointment_id}/detailer-brief", response_model=DetailerBriefResponse)
async def get_master_detailer_brief(
    appointment_id: int,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Сводка детейлера к заезду: состояние, допродажи, фото."""
    from app.modules.cars.condition import effective_condition

    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.car))
        .where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == tenant_id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    is_admin = current_user["role"] in ("admin", "super_admin")
    if appointment.master_id != current_user["id"] and not is_admin:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    insp_result = await db.execute(
        select(DetailerInspection).where(
            DetailerInspection.appointment_id == appointment.id,
            DetailerInspection.tenant_id == tenant_id,
        ).order_by(DetailerInspection.id.desc())
    )
    row = insp_result.scalars().first()
    return {
        "appointment_id": appointment.id,
        "inspect_id": row.id if row else None,
        "master_brief": (row.master_brief if row else None) or appointment.master_brief,
        "findings": (row.findings if row else None) or [],
        "upsells": (row.upsells if row else None) or [],
        "photo_count": len(row.photo_ids or []) if row else 0,
        "car_condition": effective_condition(appointment.car, appointment.car_condition),
    }

@router.get("/api/boxes", response_model=list[BoxOut])
async def get_boxes(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список всех боксов/зон тенанта."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id)
        .order_by(Box.sort_order, Box.name)
    )
    boxes = result.scalars().all()

    # Загружаем привязки услуг для всех боксов
    box_ids = [b.id for b in boxes]
    box_services_map: dict[int, list[int]] = {}
    if box_ids:
        bs_result = await db.execute(
            select(BoxService).where(
                BoxService.box_id.in_(box_ids),
                BoxService.tenant_id == tenant_id,
            )
        )
        for bs in bs_result.scalars().all():
            box_services_map.setdefault(bs.box_id, []).append(bs.service_id)

    out = []
    for b in boxes:
        bo = BoxOut.model_validate(b)
        bo.service_ids = box_services_map.get(b.id, [])
        out.append(bo)
    return out

@router.get("/api/boxes/live", response_model=BoxLiveResponse)
async def get_boxes_live(
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Сетка боксов сейчас: занятость, подготовка слота, ближайшая запись."""
    from app.modules.appointments.live_service import build_live_floor

    return await build_live_floor(db, UUID(current_user["tenant_id"]))

@router.post("/api/boxes", response_model=BoxOut)
async def create_box(
    request: BoxCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый бокс/зону."""
    tenant_id = UUID(current_user["tenant_id"])
    box = Box(
        name=request.name,
        color=request.color,
        sort_order=request.sort_order,
        is_active=request.is_active,
        tenant_id=tenant_id,
    )
    db.add(box)
    await db.commit()
    await db.refresh(box)

    # Привязываем услуги, если указаны
    if request.service_ids:
        for sid in request.service_ids:
            db.add(BoxService(box_id=box.id, service_id=sid, tenant_id=tenant_id))
        await db.commit()

    bo = BoxOut.model_validate(box)
    bo.service_ids = request.service_ids or []
    return bo

@router.put("/api/boxes/{box_id}", response_model=BoxOut)
async def update_box(
    box_id: int,
    request: BoxUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить бокс/зону."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Box).where(Box.id == box_id, Box.tenant_id == tenant_id)
    )
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=404, detail="Бокс не найден")

    update_data = request.model_dump(exclude_unset=True)
    # Обрабатываем service_ids отдельно
    service_ids = update_data.pop("service_ids", None)

    for key, value in update_data.items():
        setattr(box, key, value)

    # Обновляем привязку услуг
    if service_ids is not None:
        # Удаляем старые
        await db.execute(
            BoxService.__table__.delete().where(
                BoxService.box_id == box_id,
                BoxService.tenant_id == tenant_id,
            )
        )
        # Добавляем новые
        for sid in service_ids:
            db.add(BoxService(box_id=box_id, service_id=sid, tenant_id=tenant_id))

    await db.commit()
    await db.refresh(box)

    # Загружаем итоговые service_ids
    bs_result = await db.execute(
        select(BoxService).where(
            BoxService.box_id == box_id,
            BoxService.tenant_id == tenant_id,
        )
    )
    bo = BoxOut.model_validate(box)
    bo.service_ids = [bs.service_id for bs in bs_result.scalars().all()]
    return bo

@router.delete("/api/boxes/{box_id}")
async def delete_box(
    box_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить бокс/зону."""
    result = await db.execute(
        select(Box).where(Box.id == box_id, Box.tenant_id == UUID(current_user["tenant_id"]))
    )
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=404, detail="Бокс не найден")

    # Сбросить box_id у связанных записей
    await db.execute(
        update(Appointment).where(Appointment.box_id == box_id).values(box_id=None)
    )
    await db.delete(box)
    await db.commit()
    return {"message": f"Бокс «{box.name}» удалён"}

@router.get("/api/calendar/{master_id}", response_model=CalendarResponse)
async def get_master_calendar(
    master_id: int,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить календарь мастера на диапазон дат."""
    try:
        tenant_id = UUID(current_user["tenant_id"])

        # Получаем мастера
        result = await db.execute(select(User).where(User.id == master_id, User.tenant_id == tenant_id))
        master = result.scalar_one_or_none()
        if not master:
            raise HTTPException(status_code=404, detail="Мастер не найден")

        # Рабочие часы
        wh_result = await db.execute(
            select(WorkingHours).where(
                WorkingHours.master_id == master_id,
                WorkingHours.tenant_id == tenant_id,
            ).order_by(WorkingHours.day_of_week)
        )
        working_hours = wh_result.scalars().all()

        # Записи мастера на диапазон
        from datetime import date as date_type
        s_date = date_type.fromisoformat(start_date)
        e_date = date_type.fromisoformat(end_date)
        from datetime import datetime, time
        s_dt = datetime.combine(s_date, time.min, tzinfo=timezone.utc)
        e_dt = datetime.combine(e_date, time.max, tzinfo=timezone.utc)

        appt_result = await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.client), selectinload(Appointment.service), selectinload(Appointment.car))
            .where(
                Appointment.master_id == master_id,
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= s_dt,
                Appointment.start_time <= e_dt,
            )
            .order_by(Appointment.start_time)
        )
        appts = appt_result.scalars().all()

        # Группировка по дням
        from collections import defaultdict
        days_map: dict[str, list] = defaultdict(list)
        for a in appts:
            day_key = a.start_time.strftime("%Y-%m-%d")
            days_map[day_key].append(CalendarAppointment(
                id=a.id,
                client_id=a.client_id,
                master_id=a.master_id,
                car_id=a.car_id,
                service_id=a.service_id,
                start_time=a.start_time.isoformat(),
                end_time=a.end_time.isoformat(),
                status=a.status,
                total_price=float(a.total_price or 0),
                service_name=a.service.name if a.service else None,
                client_name=a.client.full_name if a.client else None,
                car_info=f"{a.car.make} {a.car.model}" if a.car else None,
            ))

        days = []
        current = s_date
        while current <= e_date:
            key = current.isoformat()
            days.append(CalendarDay(
                date=key,
                day_of_week=current.weekday(),
                appointments=days_map.get(key, []),
            ))
            from datetime import timedelta
            current += timedelta(days=1)

        return CalendarResponse(
            master_id=master_id,
            master_name=master.full_name,
            days=days,
            working_hours=[WorkingHoursOut.model_validate(w) for w in working_hours],
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] get_master_calendar({master_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/appointments/{appointment_id}/move")
async def move_appointment(
    appointment_id: int,
    start_time: str = Query(..., description="Новое время ISO 8601"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Перенести запись (Drag & Drop)."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    new_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    old_start_str = appt.start_time.isoformat() if appt.start_time else ""
    duration = (appt.end_time - appt.start_time).total_seconds() / 60
    appt.start_time = new_start
    appt.end_time = new_start + timedelta(minutes=duration)
    await db.commit()


    # History: log move
    from app.services.history_service import log_move as _log_move
    from datetime import datetime as _dt
    await _log_move(db, appointment_id, old_start_str, new_start.isoformat(), current_user["id"])

    return {"message": "Запись перенесена", "appointment_id": appointment_id}

@router.get("/api/masters/working-hours", response_model=list[WorkingHoursOut])
async def get_working_hours(
    master_id: int | None = Query(None),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить рабочие часы мастеров."""
    tenant_id = UUID(current_user["tenant_id"])
    stmt = select(WorkingHours).where(WorkingHours.tenant_id == tenant_id)
    if master_id:
        stmt = stmt.where(WorkingHours.master_id == master_id)
    stmt = stmt.order_by(WorkingHours.master_id, WorkingHours.day_of_week)

    result = await db.execute(stmt)
    return [WorkingHoursOut.model_validate(w) for w in result.scalars().all()]

@router.put("/api/masters/working-hours/{master_id}", response_model=list[WorkingHoursOut])
async def update_working_hours(
    master_id: int,
    hours: list[WorkingHoursUpdate],
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить рабочие часы мастера."""
    tenant_id = UUID(current_user["tenant_id"])

    # Удаляем старые
    await db.execute(
        WorkingHours.__table__.delete().where(
            WorkingHours.master_id == master_id,
            WorkingHours.tenant_id == tenant_id,
        )
    )

    # Создаём новые
    for h in hours:
        wh = WorkingHours(
            master_id=master_id,
            tenant_id=tenant_id,
            day_of_week=h.day_of_week,
            start_time=h.start_time,
            end_time=h.end_time,
            is_working_day=h.is_working_day,
        )
        db.add(wh)

    await db.commit()

    result = await db.execute(
        select(WorkingHours).where(
            WorkingHours.master_id == master_id,
            WorkingHours.tenant_id == tenant_id,
        ).order_by(WorkingHours.day_of_week)
    )
    return [WorkingHoursOut.model_validate(w) for w in result.scalars().all()]

@router.get("/api/appointments/{appointment_id}/history")
async def get_appointment_history(
    appointment_id: int,
    change_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить историю изменений записи."""
    from app.services.history_service import get_history

    items, total = await get_history(db, appointment_id, skip=skip, limit=limit, change_type=change_type)

    # Serialize with user name
    result = []
    for item in items:
        entry = HistoryEntryOut(
            id=item.id,
            appointment_id=item.appointment_id,
            change_type=item.change_type,
            field_name=item.field_name,
            old_value=item.old_value,
            new_value=item.new_value,
            created_at=item.created_at,
        )
        if item.changed_by:
            entry.changed_by = {
                "id": item.changed_by.id,
                "full_name": item.changed_by.full_name,
            }
        result.append(entry)

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/appointments/{appointment_id}/history/{history_id}")
async def get_history_detail(
    appointment_id: int,
    history_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить детали конкретного изменения."""
    result = await db.execute(
        select(AppointmentHistory)
        .options(selectinload(AppointmentHistory.changed_by))
        .where(
            AppointmentHistory.id == history_id,
            AppointmentHistory.appointment_id == appointment_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Запись истории не найдена")

    out = HistoryEntryOut(
        id=entry.id,
        appointment_id=entry.appointment_id,
        change_type=entry.change_type,
        field_name=entry.field_name,
        old_value=entry.old_value,
        new_value=entry.new_value,
        created_at=entry.created_at,
    )
    if entry.changed_by:
        out.changed_by = {"id": entry.changed_by.id, "full_name": entry.changed_by.full_name}
    return out

