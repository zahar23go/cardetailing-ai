"""HTTP API — модуль payments."""
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

@router.post("/api/payments/create", response_model=PaymentOut)
async def create_payment(
    request: PaymentCreateRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать платёж для записи."""
    # Проверяем запись
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == request.appointment_id,
            Appointment.client_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    # Проверяем, нет ли уже оплаты
    existing = await db.execute(
        select(Payment).where(
            Payment.appointment_id == request.appointment_id,
            Payment.status.in_(["pending", "succeeded"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Платёж уже создан")

    payment = Payment(
        tenant_id=UUID(current_user["tenant_id"]),
        appointment_id=request.appointment_id,
        amount=appt.total_price,
        payment_method=request.payment_method or "card",
        status="pending",
        payment_id=f"pay_{appt.id}_{int(datetime.now().timestamp())}",
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return PaymentOut.model_validate(payment)

@router.post("/api/payments/webhook")
async def payment_webhook(
    data: PaymentWebhookRequest,
    db: AsyncSession = Depends(get_db),
):
    """Webhook от платёжной системы."""
    result = await db.execute(
        select(Payment).where(Payment.payment_id == data.payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    payment.status = data.status
    await db.commit()
    return {"message": "Статус платежа обновлён"}

@router.get("/api/payments/{payment_id}/status", response_model=PaymentOut)
async def get_payment_status(
    payment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Проверить статус платежа."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return PaymentOut.model_validate(payment)

@router.post("/api/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Возврат платежа."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail="Только успешные платежи можно вернуть")

    payment.status = "refunded"
    await db.commit()
    return {"message": "Платёж возвращён", "payment_id": payment_id}

