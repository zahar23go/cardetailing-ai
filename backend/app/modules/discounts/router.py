"""HTTP API — модуль discounts."""
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

@router.post("/api/discounts/broadcast-happy-hours")
async def broadcast_happy_hours(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Рассылка клиентам о текущих Happy Hours."""
    from app.core.notification_service import create_notification

    tenant_id = UUID(current_user["tenant_id"])
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            DiscountRule.type == "happy_hours",
        )
    )
    rules = rules_result.scalars().all()
    if not rules:
        raise HTTPException(status_code=400, detail="Нет активных Happy Hours для рассылки")

    lines = []
    for r in rules:
        slot = f"{r.slot_start.strftime('%H:%M') if r.slot_start else '?'}–{r.slot_end.strftime('%H:%M') if r.slot_end else '?'}"
        days = (r.conditions or {}).get("weekdays")
        if isinstance(days, list) and days:
            names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_label = "–".join(names[d] for d in sorted(days) if 0 <= d <= 6)
        else:
            day_label = "Пн–Пт"
        lines.append(f"• {day_label} {slot}: −{r.discount_percent}%")

    title = "Счастливые часы в салоне"
    message = "Запишитесь в свободное время и получите скидку:\n" + "\n".join(lines)

    clients = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.client,
        )
    )
    client_list = clients.scalars().all()
    sent = 0
    for c in client_list:
        await create_notification(
            db,
            user_id=c.id,
            tenant_id=tenant_id,
            title=title,
            message=message,
            type="promo",
            channel="in_app",
        )
        sent += 1

    return {"sent": sent, "message": f"Рассылка отправлена {sent} клиентам"}


@router.get("/api/discounts/smart")
async def get_smart_discounts(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Погода сегодня, какие погодные акции сработают, клиенты для win-back."""
    from app.modules.discounts.smart import smart_overview

    tenant_id = UUID(current_user["tenant_id"])
    return await smart_overview(db, tenant_id)


@router.post("/api/discounts/broadcast-win-back")
async def broadcast_win_back(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Написать клиентам, которые давно не были (по активному правилу win-back)."""
    from app.core.notification_service import create_notification
    from app.modules.discounts.smart import list_win_back_candidates

    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            DiscountRule.type == "win_back",
            (DiscountRule.valid_until == None) | (DiscountRule.valid_until >= now),
        )
    )
    rules = list(rules_result.scalars().all())
    if not rules:
        raise HTTPException(status_code=400, detail="Нет активного правила «возврат клиентов»")

    min_days = min(int((r.conditions or {}).get("max_recency_days", 60)) for r in rules)
    best = max(rules, key=lambda r: r.discount_percent)
    clients = await list_win_back_candidates(db, tenant_id, min_days, now=now)
    if not clients:
        return {"sent": 0, "message": "Сейчас нет клиентов для возврата"}

    title = "Давно не виделись"
    message = (
        f"Вас не было {min_days}+ дней. Вернитесь — скидка {best.discount_percent}% "
        f"по акции «{best.name}»."
    )
    sent = 0
    for c in clients:
        await create_notification(
            db,
            user_id=c["id"],
            tenant_id=tenant_id,
            title=title,
            message=message,
            type="promo",
            channel="in_app",
        )
        sent += 1
    return {"sent": sent, "message": f"Рассылка отправлена {sent} клиентам"}


@router.get("/api/discounts")
async def get_discount_rules(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить все правила скидок тенанта."""
    stmt = (
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(DiscountRule.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(DiscountRule.created_at.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_discount_rule_to_out(r) for r in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/discounts/active")
async def get_active_discounts(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Активные скидки салона, доступные текущему клиенту."""
    tenant_id = UUID(current_user["tenant_id"])
    today = datetime.now(timezone.utc)
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            or_(
                DiscountRule.client_id.is_(None),
                DiscountRule.client_id == current_user["id"],
            ),
        )
        .order_by(DiscountRule.created_at.desc())
    )
    items = []
    for rule in result.scalars().all():
        if rule.valid_until and rule.valid_until < today:
            continue
        items.append(_discount_rule_to_out(rule))
    return {"items": items, "total": len(items)}

@router.post("/api/discounts", response_model=DiscountRuleOut)
async def create_discount_rule(
    request: DiscountRuleCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новое правило скидки."""
    tenant_id = UUID(current_user["tenant_id"])

    # Проверка на дубликат по имени
    existing = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.name == request.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Скидка с названием «{request.name}» уже существует")

    slot_start = _parse_time_str(request.slot_start)
    slot_end = _parse_time_str(request.slot_end)
    valid_until = _parse_date_str(request.valid_until)

    rule = DiscountRule(
        name=request.name,
        type=request.type,
        conditions=request.conditions or {},
        discount_percent=request.discount_percent,
        slot_start=slot_start,
        slot_end=slot_end,
        service_id=request.service_id,
        client_id=request.client_id,
        valid_until=valid_until,
        is_active=request.is_active if request.is_active is not None else True,
        tenant_id=tenant_id,
    )
    try:
        db.add(rule)
        await db.commit()
        result = await db.execute(
            select(DiscountRule)
            .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
            .where(DiscountRule.id == rule.id)
        )
        rule = result.scalar_one()
        # Уведомление — не должно ломать создание скидки
        try:
            await _notify_discount_created(db, rule, current_user)
        except Exception as notify_err:
            print(f"[WARN] Notification failed: {notify_err}")
        return _discount_rule_to_out(rule)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] Create discount failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/api/discounts/{rule_id}", response_model=DiscountRuleOut)
async def update_discount_rule(
    rule_id: int,
    request: DiscountRuleUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить правило скидки."""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id,
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило скидки не найдено")

    update_data = request.model_dump(exclude_unset=True)
    if "slot_start" in update_data:
        update_data["slot_start"] = _parse_time_str(update_data["slot_start"])
    if "slot_end" in update_data:
        update_data["slot_end"] = _parse_time_str(update_data["slot_end"])
    if "valid_until" in update_data:
        update_data["valid_until"] = _parse_date_str(update_data["valid_until"])

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    # Reload with relations
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(DiscountRule.id == rule.id)
    )
    rule = result.scalar_one()
    return _discount_rule_to_out(rule)

@router.delete("/api/discounts/{rule_id}")
async def delete_discount_rule(
    rule_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить правило скидки."""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id,
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило скидки не найдено")

    name = rule.name
    try:
        await db.delete(rule)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось удалить правило «{name}»: {str(e)}",
        )
    return {"message": f"Правило скидки «{name}» удалено"}

@router.get("/api/loyalty/points")
async def get_loyalty_points(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    client_id: int | None = Query(None, description="Фильтр по ID клиента (возвращает одного)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить баланс баллов клиентов."""
    tenant_id = UUID(current_user["tenant_id"])

    if client_id is not None:
        # Один конкретный клиент — ищем его баллы напрямую
        points_result = await db.execute(
            select(LoyaltyPoints).where(
                LoyaltyPoints.client_id == client_id,
                LoyaltyPoints.tenant_id == tenant_id,
            )
        )
        lp = points_result.scalar_one_or_none()
        user_result = await db.execute(
            select(User).where(User.id == client_id, User.tenant_id == tenant_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return {"items": [], "total": 0}

        return {
            "items": [LoyaltyPointsSummary(
                client_id=user.id,
                full_name=user.full_name,
                phone=user.phone,
                balance=lp.balance if lp else 0,
                total_earned=lp.total_earned if lp else 0,
                total_spent=lp.total_spent if lp else 0,
            )],
            "total": 1,
        }

    # Все клиенты тенанта (с пагинацией)
    clients_stmt = (
        select(User)
        .where(User.role == "client", User.tenant_id == tenant_id)
        .order_by(User.full_name)
    )
    # Count total clients first
    count_stmt = select(func.count()).select_from(clients_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    clients_result = await db.execute(clients_stmt.offset(skip).limit(limit))
    clients = clients_result.scalars().all()

    # Их баллы
    client_ids = [c.id for c in clients]
    if not client_ids:
        return {"items": [], "total": 0}

    points_result = await db.execute(
        select(LoyaltyPoints).where(LoyaltyPoints.client_id.in_(client_ids))
    )
    points_map: dict[int, LoyaltyPoints] = {}
    for p in points_result.scalars().all():
        points_map[p.client_id] = p

    result = []
    for c in clients:
        lp = points_map.get(c.id)
        result.append(LoyaltyPointsSummary(
            client_id=c.id,
            full_name=c.full_name,
            phone=c.phone,
            balance=lp.balance if lp else 0,
            total_earned=lp.total_earned if lp else 0,
            total_spent=lp.total_spent if lp else 0,
        ))

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/api/loyalty/tiers", response_model=list[LoyaltyTierConfigOut])
async def get_loyalty_tiers(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить конфигурацию уровней лояльности."""
    result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(LoyaltyTierConfig.min_total_spent.asc())
    )
    return [LoyaltyTierConfigOut.model_validate(t) for t in result.scalars().all()]

@router.put("/api/loyalty/tiers", response_model=list[LoyaltyTierConfigOut])
async def update_loyalty_tiers(
    tiers: list[LoyaltyTierConfigUpdate],
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить конфигурацию уровней лояльности."""
    tenant_id = UUID(current_user["tenant_id"])

    # Delete old config
    await db.execute(
        LoyaltyTierConfig.__table__.delete().where(
            LoyaltyTierConfig.tenant_id == tenant_id
        )
    )

    # Insert new
    for t in tiers:
        config = LoyaltyTierConfig(
            tenant_id=tenant_id,
            tier=t.tier,
            min_total_spent=t.min_total_spent,
            min_visits=t.min_visits,
            discount_percent=t.discount_percent,
            bonus_multiplier=t.bonus_multiplier,
            color=t.color,
        )
        db.add(config)

    await db.commit()

    result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == tenant_id)
        .order_by(LoyaltyTierConfig.min_total_spent.asc())
    )
    return [LoyaltyTierConfigOut.model_validate(t) for t in result.scalars().all()]

@router.get("/api/loyalty/my-tier", response_model=ClientTierOut)
async def get_my_tier(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить свой уровень лояльности."""
    from app.services.loyalty_service import get_client_tier_info
    from app.models import User

    await recalculate_tier_if_needed(db, current_user["id"], UUID(current_user["tenant_id"]))

    info = await get_client_tier_info(db, current_user["id"], UUID(current_user["tenant_id"]))

    user_result = await db.execute(
        select(User).where(User.id == current_user["id"])
    )
    user = user_result.scalar_one()

    return ClientTierOut(
        client_id=current_user["id"],
        full_name=user.full_name,
        phone=user.phone,
        **info,
    )

@router.get("/api/discounts/by-service/{service_id}", response_model=list[dict])
async def get_discounts_by_service(
    service_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить скидки для конкретной услуги."""
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
            DiscountRule.service_id == service_id,
            DiscountRule.is_active == True,
        )
        .order_by(DiscountRule.created_at.desc())
    )
    return [_discount_rule_to_out(r) for r in result.scalars().all()]

@router.get("/api/discounts/by-client/{client_id}", response_model=list[dict])
async def get_discounts_by_client(
    client_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить персональные скидки для клиента."""
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
            DiscountRule.client_id == client_id,
            DiscountRule.is_active == True,
        )
        .order_by(DiscountRule.created_at.desc())
    )
    return [_discount_rule_to_out(r) for r in result.scalars().all()]

@router.get("/api/discounts/analytics")
async def get_discount_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика эффективности скидок."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Все правила скидок
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    rules = rules_result.scalars().all()

    # Все применения скидок (ClientDiscount)
    cd_result = await db.execute(
        select(ClientDiscount)
        .options(selectinload(ClientDiscount.discount_rule))
        .where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    client_discounts = cd_result.scalars().all()

    # Статистика по каждому правилу
    rule_stats = {}
    for cd in client_discounts:
        rule_id = cd.discount_rule_id
        if rule_id not in rule_stats:
            rule_stats[rule_id] = {
                "count": 0,
                "total_discount_amount": 0.0,
                "total_original_price": 0.0,
            }
        rule_stats[rule_id]["count"] += 1
        rule_stats[rule_id]["total_discount_amount"] += float(cd.applied_amount or 0)

        # Ищем оригинальную цену в appointment
        if cd.appointment_id:
            appt_result = await db.execute(
                select(Appointment).where(Appointment.id == cd.appointment_id)
            )
            appt = appt_result.scalar_one_or_none()
            if appt:
                original = float(appt.total_price or 0) + float(appt.discount_applied or 0)
                rule_stats[rule_id]["total_original_price"] += original

    # Собираем результат
    analytics = []
    for rule in rules:
        stats = rule_stats.get(rule.id, {"count": 0, "total_discount_amount": 0.0, "total_original_price": 0.0})
        roi = 0
        if stats["total_discount_amount"] > 0:
            roi = round(
                (stats["total_original_price"] - stats["total_discount_amount"]) / stats["total_discount_amount"] * 100,
                1,
            ) if stats["total_discount_amount"] else 0

        analytics.append({
            "rule_id": rule.id,
            "rule_name": rule.name,
            "rule_type": rule.type,
            "discount_percent": rule.discount_percent,
            "is_active": rule.is_active,
            "usage_count": stats["count"],
            "total_discount_amount": round(stats["total_discount_amount"], 2),
            "total_original_price": round(stats["total_original_price"], 2),
            "roi_percent": roi,
        })

    # Общая статистика
    total_used = sum(a["usage_count"] for a in analytics)
    total_discounted = sum(a["total_discount_amount"] for a in analytics)

    return {
        "rules": analytics,
        "summary": {
            "total_rules": len(rules),
            "active_rules": sum(1 for r in rules if r.is_active),
            "total_discount_uses": total_used,
            "total_discount_amount": round(total_discounted, 2),
        },
    }

