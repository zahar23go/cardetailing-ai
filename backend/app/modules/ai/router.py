"""HTTP API — модуль ai."""
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

@router.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(request: ChatRequest):
    response = await get_ai_response(request.message)
    return ChatResponse(response=response)

@router.post("/api/ai/financier", response_model=FinancierResponse)
async def ai_financier(
    request: FinancierRequest,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """AI-финансист: аналитика бизнеса + рекомендации."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Сбор контекста ---

    # Всего клиентов / мастеров
    clients_result = await db.execute(
        select(User).where(User.role == "client", User.tenant_id == tenant_id)
    )
    total_clients = len(clients_result.scalars().all())

    masters_result = await db.execute(
        select(User).where(User.role == "master", User.tenant_id == tenant_id)
    )
    total_masters = len(masters_result.scalars().all())

    # Выручка сегодня / месяц
    month_appts = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    month_list = month_appts.scalars().all()
    month_revenue = sum(float(a.total_price or 0) for a in month_list if a.status == "completed")

    today_appts = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= today_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    today_list = today_appts.scalars().all()
    today_revenue = sum(float(a.total_price or 0) for a in today_list if a.status == "completed")

    # Записи
    total_appts = len(month_list)
    completed_appts = sum(1 for a in month_list if a.status == "completed")
    pending_appts = sum(1 for a in month_list if a.status == "pending")

    # Эффективность мастеров
    master_stats = {}
    for a in month_list:
        if a.master_id and a.status == "completed":
            master_name = f"мастер #{a.master_id}"
            if a.master_id not in master_stats:
                result = await db.execute(select(User).where(User.id == a.master_id))
                master = result.scalar_one_or_none()
                master_name = master.full_name if master else master_name
                master_stats[a.master_id] = {"name": master_name, "completed": 0, "revenue": 0.0}
            master_stats[a.master_id]["completed"] += 1
            master_stats[a.master_id]["revenue"] += float(a.total_price or 0)

    # Популярность услуг
    service_popularity = {}
    for a in month_list:
        if a.service_id:
            if a.service_id not in service_popularity:
                srv_result = await db.execute(select(Service).where(Service.id == a.service_id))
                srv = srv_result.scalar_one_or_none()
                service_popularity[a.service_id] = {
                    "name": srv.name if srv else f"услуга #{a.service_id}",
                    "count": 0,
                }
            service_popularity[a.service_id]["count"] += 1

    # Формируем текст контекста
    ctx_lines = [
        f"• Всего клиентов: {total_clients}",
        f"• Всего мастеров: {total_masters}",
        f"• Записей за месяц: {total_appts} (завершено: {completed_appts}, ожидают: {pending_appts})",
        f"• Записей сегодня: {len(today_list)}",
        f"• Выручка за месяц: {month_revenue:.0f} руб.",
        f"• Выручка сегодня: {today_revenue:.0f} руб.",
    ]

    if master_stats:
        ctx_lines.append("\nЭффективность мастеров (за месяц):")
        for m in sorted(master_stats.values(), key=lambda x: x["completed"], reverse=True):
            ctx_lines.append(f"  • {m['name']}: {m['completed']} работ(ы), {m['revenue']:.0f} руб.")

    if service_popularity:
        ctx_lines.append("\nПопулярность услуг (за месяц):")
        for s in sorted(service_popularity.values(), key=lambda x: x["count"], reverse=True):
            ctx_lines.append(f"  • {s['name']}: {s['count']} записей")

    business_context = "\n".join(ctx_lines)
    response = await get_financier_response(request.question, business_context)
    return FinancierResponse(response=response)

@router.post("/api/ai/consultant", response_model=FinancierResponse)
async def ai_consultant(
    request: FinancierRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-консультант для клиентов: помогает выбрать услуги, отвечает на вопросы."""
    tenant_id = UUID(current_user["tenant_id"])

    # Загружаем все услуги салона
    services_result = await db.execute(
        select(Service).where(
            Service.is_active == True,
            Service.tenant_id == tenant_id,
        ).order_by(Service.name)
    )
    services = services_result.scalars().all()

    # Загружаем количество фото в портфолио по каждой услуге
    portfolio_counts: dict[int, int] = {}
    if services:
        sids = [s.id for s in services]
        count_result = await db.execute(
            select(Photo.service_id, func.count(Photo.id))
            .where(
                Photo.tenant_id == tenant_id,
                Photo.entity_type == "portfolio",
                Photo.service_id.in_(sids),
            )
            .group_by(Photo.service_id)
        )
        for row in count_result.all():
            portfolio_counts[row[0]] = row[1]

    # Формируем контекст услуг
    services_lines = []
    for s in services:
        cat = s.category or "Без категории"
        photo_count = portfolio_counts.get(s.id, 0)
        photo_hint = f", фото в портфолио: {photo_count}" if photo_count else ""
        services_lines.append(
            f"• {s.name} (категория: {cat}) — {s.price} руб., ~{s.duration} мин., "
            f"описание: {s.description or '—'}{photo_hint}"
        )

    services_context = "\n".join(services_lines) if services_lines else "Услуги временно не загружены."

    response = await get_consultant_response(request.question, services_context)
    return FinancierResponse(response=response)

