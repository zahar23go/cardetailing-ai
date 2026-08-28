"""HTTP API — модуль tech_cards."""
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

@router.post("/api/tech-cards/upload-photo", response_model=TechCardPhotoOut)
async def upload_tech_card_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(_require_admin),
):
    """Загрузить фото шага техкарты. URL сохраняется в блоке."""
    contents = await file.read()
    try:
        validate_image(contents, file.filename or "image.jpg")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    filename = generate_filename(file.filename or "image.jpg")
    url, thumb_url = save_file_local(
        contents,
        f"tech-cards/{current_user['tenant_id']}",
        filename,
    )
    return TechCardPhotoOut(url=url, thumbnail_url=thumb_url)

@router.get("/api/tech-cards")
async def get_tech_cards(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
):
    """Список техкарт с блоками и материалами."""
    from app.services.tech_cards_service import list_tech_cards, tech_card_to_out
    items, total = await list_tech_cards(
        db,
        UUID(current_user["tenant_id"]),
        skip=skip,
        limit=limit,
        service_id=service_id,
        is_active=is_active,
        search=search,
    )
    return {
        "items": [tech_card_to_out(c) for c in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/tech-cards/{card_id}", response_model=TechCardOut)
async def get_tech_card_by_id(
    card_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить техкарту по id."""
    from app.services.tech_cards_service import get_tech_card, tech_card_to_out
    card = await get_tech_card(db, UUID(current_user["tenant_id"]), card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

@router.post("/api/tech-cards", response_model=TechCardOut, status_code=201)
async def create_tech_card_endpoint(
    request: TechCardCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать техкарту для услуги."""
    from app.services.tech_cards_service import create_tech_card, tech_card_to_out
    try:
        card = await create_tech_card(db, UUID(current_user["tenant_id"]), request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return tech_card_to_out(card)

@router.put("/api/tech-cards/{card_id}", response_model=TechCardOut)
async def update_tech_card_endpoint(
    card_id: int,
    request: TechCardUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить техкарту, блоки и состав материалов."""
    from app.services.tech_cards_service import update_tech_card, tech_card_to_out
    try:
        card = await update_tech_card(
            db, UUID(current_user["tenant_id"]), card_id, request
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

@router.delete("/api/tech-cards/{card_id}")
async def delete_tech_card_endpoint(
    card_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить техкарту."""
    from app.services.tech_cards_service import delete_tech_card
    ok = await delete_tech_card(db, UUID(current_user["tenant_id"]), card_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return {"message": "Tech card deleted"}

@router.post("/api/tech-cards/{card_id}/blocks", response_model=TechCardOut, status_code=201)
async def add_tech_card_block(
    card_id: int,
    request: TechCardBlockIn,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Добавить шаг в техкарту."""
    from app.services.tech_cards_service import add_block, tech_card_to_out
    try:
        card = await add_block(db, UUID(current_user["tenant_id"]), card_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

@router.put("/api/tech-cards/{card_id}/blocks/reorder", response_model=TechCardOut)
async def reorder_tech_card_blocks(
    card_id: int,
    request: TechCardReorderIn,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Изменить порядок шагов техкарты."""
    from app.services.tech_cards_service import reorder_blocks, tech_card_to_out
    try:
        card = await reorder_blocks(
            db, UUID(current_user["tenant_id"]), card_id, request.block_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

@router.put("/api/tech-cards/{card_id}/blocks/{block_id}", response_model=TechCardOut)
async def update_tech_card_block(
    card_id: int,
    block_id: int,
    request: TechCardBlockIn,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить шаг техкарты."""
    from app.services.tech_cards_service import update_block, tech_card_to_out
    try:
        card = await update_block(
            db, UUID(current_user["tenant_id"]), card_id, block_id, request,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

@router.delete("/api/tech-cards/{card_id}/blocks/{block_id}", response_model=TechCardOut)
async def delete_tech_card_block(
    card_id: int,
    block_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить шаг техкарты."""
    from app.services.tech_cards_service import delete_block, tech_card_to_out
    try:
        card = await delete_block(db, UUID(current_user["tenant_id"]), card_id, block_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    return tech_card_to_out(card)

