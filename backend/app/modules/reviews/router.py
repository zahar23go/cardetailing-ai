"""HTTP API — модуль reviews."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin as _require_admin
from app.core.database import get_db
from app.core.endpoint_helpers import _paginate
from app.models import Review
from app.modules.core.schemas import PaginatedResponse
from app.modules.reviews.schemas import (
    ReviewImportRequest,
    ReviewImportResult,
    ReviewIn,
    ReviewOut,
    ReviewVerdictOut,
)

router = APIRouter()


@router.get("/api/reviews", response_model=PaginatedResponse[ReviewOut])
async def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source: str | None = Query(None),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список отзывов салона."""
    stmt = (
        select(Review)
        .where(Review.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(Review.id.desc())
    )
    if source:
        stmt = stmt.where(Review.source == source)
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[ReviewOut](
        items=[ReviewOut.model_validate(r) for r in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/api/reviews/verdict", response_model=ReviewVerdictOut)
async def get_reviews_verdict(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Последний вердикт ИИ по качеству услуг (без пересчёта)."""
    from app.modules.reviews.service import latest_verdict

    verdict = await latest_verdict(db, UUID(current_user["tenant_id"]))
    if verdict is None:
        return ReviewVerdictOut(reviews_count=0, source="none")
    return ReviewVerdictOut(**verdict)


@router.post("/api/reviews/analyze", response_model=ReviewVerdictOut)
async def analyze_reviews(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Проанализировать отзывы через ИИ и сохранить вердикт."""
    from app.modules.reviews.service import analyze_reviews as _analyze

    return await _analyze(db, UUID(current_user["tenant_id"]))


@router.post("/api/reviews/import", response_model=ReviewImportResult)
async def import_reviews(
    request: ReviewImportRequest,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Массовый импорт отзывов (вставка вручную или внешний сборщик)."""
    from app.modules.reviews.service import import_reviews as _import

    imported, skipped = await _import(db, UUID(current_user["tenant_id"]), request.reviews)
    return ReviewImportResult(imported=imported, skipped=skipped, total=len(request.reviews))


@router.post("/api/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    request: ReviewIn,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Добавить один отзыв вручную."""
    from app.modules.reviews.service import import_reviews as _import

    tenant_id = UUID(current_user["tenant_id"])
    await _import(db, tenant_id, [request])
    result = await db.execute(
        select(Review)
        .where(Review.tenant_id == tenant_id)
        .order_by(Review.id.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=400, detail="Не удалось сохранить отзыв")
    return ReviewOut.model_validate(review)


@router.delete("/api/reviews/{review_id}")
async def delete_review(
    review_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить отзыв."""
    result = await db.execute(
        select(Review).where(
            Review.id == review_id,
            Review.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    await db.delete(review)
    await db.commit()
    return {"message": "Отзыв удалён"}
