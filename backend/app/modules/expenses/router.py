"""HTTP API — модуль expenses."""
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

@router.get("/api/expenses/categories", response_model=list[ExpenseCategoryItem])
async def get_expense_categories(current_user: dict = Depends(_require_admin)):
    """Справочник категорий и подкатегорий затрат (RU)."""
    return [ExpenseCategoryItem(**c) for c in EXPENSE_CATALOG]

@router.get("/api/expenses")
async def get_expenses(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: str | None = Query(None),
    payment_status: str | None = Query(None),
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
):
    """Список расходов с фильтрами."""
    tenant_id = UUID(current_user["tenant_id"])
    filters = [Expense.tenant_id == tenant_id]
    if category:
        filters.append(Expense.category == category)
    if payment_status:
        filters.append(Expense.payment_status == payment_status)
    df = _parse_optional_dt(date_from)
    dt = _parse_optional_dt(date_to)
    if df:
        filters.append(Expense.expense_date >= df)
    if dt:
        # inclusive end of day
        if dt.hour == 0 and dt.minute == 0:
            dt = dt.replace(hour=23, minute=59, second=59)
        filters.append(Expense.expense_date <= dt)

    stmt = select(Expense).where(*filters).order_by(Expense.expense_date.desc())
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_expense_to_out(e) for e in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.post("/api/expenses", response_model=ExpenseOut)
async def create_expense(
    request: ExpenseCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый расход."""
    expense = Expense(
        name=request.name,
        amount=request.amount,
        category=request.category or "other",
        subcategory=request.subcategory,
        payment_status=request.payment_status or "paid",
        period_type=request.period_type or "monthly",
        period_start=_parse_optional_dt(request.period_start),
        period_end=_parse_optional_dt(request.period_end),
        expense_date=_parse_optional_dt(request.expense_date) or datetime.now(timezone.utc),
        notes=request.notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return _expense_to_out(expense)

@router.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: int,
    request: ExpenseUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить расход."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = request.model_dump(exclude_unset=True)
    for key in ("expense_date", "period_start", "period_end"):
        if key in update_data:
            update_data[key] = _parse_optional_dt(update_data[key])

    for key, value in update_data.items():
        setattr(expense, key, value)

    await db.commit()
    await db.refresh(expense)
    return _expense_to_out(expense)

@router.delete("/api/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить расход."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()
    return {"message": "Expense deleted"}

