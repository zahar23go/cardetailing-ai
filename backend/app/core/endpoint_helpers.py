"""Хелперы хендлеров (без смены логики). Импортируются модульными роутерами."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from uuid import UUID

from fastapi import Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.image_service import validate_image, save_file_local, generate_filename, delete_file_local
from app.finance_formulas import resolve_service_cost, service_margin_percent
from app.models import *  # noqa: F401,F403
from app.schemas import *  # noqa: F401,F403

MAX_PHOTOS_PER_ENTITY = 20

# Общие опции загрузки связей Appointment — предотвращает MissingGreenlet
_APPT_LOAD = (
    selectinload(Appointment.client),
    selectinload(Appointment.service),
    selectinload(Appointment.car),
    selectinload(Appointment.master),
    selectinload(Appointment.box),
)

EXPENSE_CATALOG: list[dict] = [
    {"key": "rent", "label": "Аренда", "subcategories": ["Помещение", "Парковка", "Склад", "Оборудование в аренду"]},
    {"key": "salary", "label": "Зарплата", "subcategories": ["Оклад", "Премии", "Налоги с ФОТ", "Подрядчики"]},
    {"key": "utilities", "label": "Коммунальные услуги", "subcategories": ["Электричество", "Вода", "Отопление", "Интернет", "Вывоз мусора"]},
    {"key": "marketing", "label": "Реклама", "subcategories": ["Онлайн-реклама", "Офлайн", "Блогеры / партнёры", "Полиграфия"]},
    {"key": "supplies", "label": "Расходники и материалы", "subcategories": ["Химия", "Расходники", "Инвентарь", "Спецодежда"]},
    {"key": "equipment", "label": "Оборудование", "subcategories": ["Покупка", "Ремонт", "Обслуживание", "Амортизация"]},
    {"key": "taxes", "label": "Налоги и сборы", "subcategories": ["УСН / НДС", "Страховые взносы", "Лицензии", "Штрафы"]},
    {"key": "insurance", "label": "Страхование", "subcategories": ["Имущество", "Ответственность", "Сотрудники"]},
    {"key": "software", "label": "ПО и сервисы", "subcategories": ["CRM / SaaS", "Бухгалтерия", "Связь", "Облако"]},
    {"key": "transport", "label": "Транспорт", "subcategories": ["ГСМ", "Такси / доставка", "Ремонт авто"]},
    {"key": "other", "label": "Прочее", "subcategories": ["Канцелярия", "Обучение", "Представительские", "Другое"]},
]

EXPENSE_CAT_LABELS = {c["key"]: c["label"] for c in EXPENSE_CATALOG}


def _service_to_out(service: Service) -> ServiceOut:
    from app.finance_formulas import resolve_service_cost, service_margin_percent
    price = float(service.price or 0)
    cost = resolve_service_cost(
        getattr(service, "cost_price", None),
        service.material_cost,
    )
    material = float(service.material_cost or 0)
    margin = service_margin_percent(price, cost)
    return ServiceOut(
        id=service.id,
        name=service.name,
        description=service.description,
        category=service.category,
        price=price,
        duration=service.duration,
        material_cost=material,
        cost_price=cost,
        margin_percent=margin,
        is_active=bool(service.is_active),
        created_at=service.created_at,
    )

def _parse_time_str(value: str | None) -> time | None:
    """Convert 'HH:MM' string to datetime.time or None."""
    if not value:
        return None
    try:
        parts = value.strip().split(':')
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None

def _discount_rule_to_out(rule) -> dict:
    """Convert DiscountRule ORM to dict with slot times and related names."""
    return {
        "id": rule.id,
        "name": rule.name,
        "type": rule.type,
        "conditions": rule.conditions,
        "discount_percent": rule.discount_percent,
        "slot_start": rule.slot_start.strftime('%H:%M') if rule.slot_start else None,
        "slot_end": rule.slot_end.strftime('%H:%M') if rule.slot_end else None,
        "service_id": rule.service_id,
        "service_name": rule.service.name if rule.service else None,
        "client_id": rule.client_id,
        "client_name": rule.client.full_name if rule.client else None,
        "valid_until": rule.valid_until.isoformat() if rule.valid_until else None,
        "is_active": rule.is_active,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }

async def _paginate(db: AsyncSession, stmt, skip: int = 0, limit: int = 20):
    """Execute a SELECT statement with pagination.

    Returns (items_list, total_count).
    Uses a separate COUNT query for the total.
    """
    # Count total rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Apply pagination
    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()

    return items, total

def _serialize_appointment(appointment):
    return {
        "id": appointment.id,
        "client_id": appointment.client_id,
        "master_id": appointment.master_id,
        "car_id": appointment.car_id,
        "service_id": appointment.service_id,
        "box_id": appointment.box_id,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "status": appointment.status if appointment.status else None,
        "total_price": float(appointment.total_price) if appointment.total_price is not None else 0,
        "discount_applied": float(appointment.discount_applied) if appointment.discount_applied is not None else 0,
        "client_notes": appointment.client_notes,
        "master_brief": appointment.master_brief,
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at,
        "service_name": appointment.service.name if appointment.service else None,
        "client": {
            "id": appointment.client.id,
            "full_name": appointment.client.full_name,
            "phone": appointment.client.phone,
        } if appointment.client else None,
        "master": {
            "id": appointment.master.id,
            "full_name": appointment.master.full_name,
        } if appointment.master else None,
        "car": {
            "id": appointment.car.id,
            "make": appointment.car.make,
            "model": appointment.car.model,
            "license_plate": appointment.car.license_plate,
            "vin": getattr(appointment.car, "vin", None),
        } if appointment.car else None,
        "service": {
            "id": appointment.service.id,
            "name": appointment.service.name,
            "price": float(appointment.service.price),
        } if appointment.service else None,
    }

def _parse_optional_dt(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None

def _expense_to_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id,
        name=e.name,
        amount=float(e.amount or 0),
        category=e.category or "other",
        subcategory=getattr(e, "subcategory", None),
        payment_status=getattr(e, "payment_status", None) or "paid",
        period_type=getattr(e, "period_type", None) or "monthly",
        period_start=getattr(e, "period_start", None),
        period_end=getattr(e, "period_end", None),
        expense_date=e.expense_date,
        notes=e.notes,
        created_at=e.created_at,
        updated_at=getattr(e, "updated_at", None),
    )

def _discount_percent_relative(hour_load: float, peak_load: float) -> int:
    """Happy Hours только там, где загрузка заметно ниже пика группы."""
    from app.finance_formulas import discount_percent_relative
    return discount_percent_relative(hour_load, peak_load)

def _merge_hour_suggestions(
    hour_percents: dict[int, tuple[int, float]],
    weekdays: list[int],
    weekday_label: str,
    prefix: str,
) -> list[DiscountSuggestion]:
    """Склеивает соседние часы с одинаковым % (пики с 0% разрывают цепочку)."""
    suggestions: list[DiscountSuggestion] = []
    hours = sorted(h for h, (p, _) in hour_percents.items() if p > 0)
    if not hours:
        return suggestions

    start = hours[0]
    prev = hours[0]
    cur_pct, _ = hour_percents[start]

    def flush(s: int, e: int, pct: int, avg: float):
        if pct <= 0:
            return
        suggestions.append(DiscountSuggestion(
            key=f"{prefix}-{s}-{e}-{pct}",
            name=f"Happy Hours {weekday_label} {s:02d}:00–{e:02d}:00",
            hour_start=f"{s:02d}:00",
            hour_end=f"{e:02d}:00",
            weekdays=weekdays,
            weekday_label=weekday_label,
            discount_percent=pct,
            avg_load=round(avg, 2),
            reason=(
                f"Загрузка {avg:.2f} отн. пика группы → скидка {pct}%. "
                f"Свободный слот на теплокарте — Happy Hours подстегнут спрос."
            ),
        ))

    avgs = [hour_percents[start][1]]
    for h in hours[1:]:
        pct, avg = hour_percents[h]
        if h == prev + 1 and pct == cur_pct:
            prev = h
            avgs.append(avg)
            continue
        flush(start, prev + 1, cur_pct, sum(avgs) / len(avgs))
        start = prev = h
        cur_pct = pct
        avgs = [avg]
    flush(start, prev + 1, cur_pct, sum(avgs) / len(avgs))
    return suggestions

def _build_group_hour_percents(
    weekdays: list[int],
    avg_for,
) -> dict[int, tuple[int, float]]:
    """
    Яркость часа = max по дням группы (как на теплокарте).
    Пик = max по часам. Скидка только ниже пика.
    """
    hour_loads: dict[int, float] = {}
    for hour in range(8, 23):
        day_avgs = [avg_for(d, hour) for d in weekdays]
        hour_loads[hour] = max(day_avgs) if day_avgs else 0.0

    peak = max(hour_loads.values()) if hour_loads else 0.0
    hour_percents: dict[int, tuple[int, float]] = {}
    for hour, load in hour_loads.items():
        mean_load = sum(avg_for(d, hour) for d in weekdays) / max(len(weekdays), 1)
        pct = _discount_percent_relative(load, peak)
        hour_percents[hour] = (pct, mean_load)
    return hour_percents

def _percent_from_priority(priority: float) -> int:
    """≥0.7 → 20–30%, 0.45–0.69 → 10–20%."""
    from app.finance_formulas import percent_from_priority
    return percent_from_priority(priority)

async def _compute_service_discount_recs(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ServiceDiscountRecommendation]:
    """
    Авто-рекомендации скидок по услугам (бухлогика салона).

    Цель:
    - подстегнуть просевшие по количеству записей;
    - подстегнуть низкомаржинальные (объём → списать постоянные на них);
    - высокомаржинальные с нормальным спросом НЕ резать (на них зарабатываем).

    Формула приоритета:
      volume_need = 1 − популярность (0…1)
      margin_need = 1 − маржа (себест./цена)
      priority = volume_need×0.55 + margin_need×0.45
    + давление постоянных расходов усиливает % на низкомаржинальных.
    """
    now = datetime.now(timezone.utc)
    cur_from = now - timedelta(days=30)
    prev_from = now - timedelta(days=60)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    services = (
        await db.execute(
            select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
        )
    ).scalars().all()
    if not services:
        return []

    appts = (
        await db.execute(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= prev_from,
                Appointment.start_time <= now,
                Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
            )
        )
    ).scalars().all()

    stats: dict[int, dict] = {
        s.id: {"cur": 0, "prev": 0, "service": s} for s in services
    }
    revenue_month = 0.0
    for a in appts:
        sid = a.service_id
        if a.start_time >= month_start:
            revenue_month += float(a.total_price or 0)
        if sid not in stats:
            continue
        if a.start_time >= cur_from:
            stats[sid]["cur"] += 1
        elif a.start_time >= prev_from:
            stats[sid]["prev"] += 1

    # Постоянные расходы текущего месяца (давление на маржу)
    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.tenant_id == tenant_id,
                Expense.expense_date >= month_start,
                Expense.expense_date <= now,
            )
        )
    ).scalars().all()
    fixed_month = sum(float(e.amount or 0) for e in expenses)
    overhead_pressure = fixed_month / max(revenue_month, 1.0)

    max_bookings = max((v["cur"] for v in stats.values()), default=0) or 1
    booking_counts = [v["cur"] for v in stats.values()]
    median_bookings = sorted(booking_counts)[len(booking_counts) // 2] if booking_counts else 0

    margins_raw: list[float] = []
    service_margin: dict[int, float] = {}
    for s in services:
        price = float(s.price or 0)
        cost = float(getattr(s, "cost_price", None) or 0) or float(s.material_cost or 0)
        raw = ((price - cost) / price) if price > 0 else 0.0
        raw = max(0.0, min(1.0, raw))
        service_margin[s.id] = raw
        margins_raw.append(raw)
    margin_median = sorted(margins_raw)[len(margins_raw) // 2] if margins_raw else 0.5

    # Порог «высокая маржа — защищаем цену»
    HIGH_MARGIN_PROTECT = 0.70

    old_pending = (
        await db.execute(
            select(ServiceDiscountRecommendation).where(
                ServiceDiscountRecommendation.tenant_id == tenant_id,
                ServiceDiscountRecommendation.status == "pending",
            )
        )
    ).scalars().all()
    for row in old_pending:
        await db.delete(row)

    created: list[ServiceDiscountRecommendation] = []
    for s in services:
        price = float(s.price or 0)
        cost = float(getattr(s, "cost_price", None) or 0) or float(s.material_cost or 0)
        margin_raw = service_margin[s.id]
        bookings = stats[s.id]["cur"]
        prev = stats[s.id]["prev"]
        popularity = bookings / max_bookings

        volume_need = 1.0 - popularity
        if bookings == 0:
            volume_need = 1.0
        elif bookings <= max(median_bookings, 1):
            volume_need = max(volume_need, 0.65)

        margin_need = 1.0 - margin_raw
        # индекс для UI (как раньше): относительно медианы каталога
        if margin_median >= 0.999:
            margin_index = 1.0
        else:
            # выше медианы → ближе к 1, ниже → ближе к 0
            span = max(1.0 - margin_median, margin_median, 0.01)
            margin_index = max(0.0, min(1.0, 0.5 + (margin_raw - margin_median) / (2 * span)))

        is_low_volume = bookings <= max(1, int(max_bookings * 0.45)) or popularity <= 0.45
        is_low_margin = margin_raw <= margin_median or margin_raw < 0.55

        # Высокомаржинальные с нормальным/хорошим спросом — не трогаем
        if margin_raw >= HIGH_MARGIN_PROTECT and not is_low_volume:
            continue

        # Нужна скидка только если просадка по объёму ИЛИ низкая маржа
        if not (is_low_volume or is_low_margin):
            continue

        priority = volume_need * 0.55 + margin_need * 0.45
        if priority < 0.40:
            continue

        suggested = _percent_from_priority(priority)
        if suggested <= 0:
            continue

        # На высокомаржинальных, но просевших — только мягкая скидка (заполнить слот)
        if margin_raw >= HIGH_MARGIN_PROTECT and is_low_volume:
            suggested = min(suggested, 12)
            scenario = "volume_fill"
            reason = (
                f"Просадка по записям: {bookings} за 30д (макс в каталоге {max_bookings}). "
                f"Маржа высокая ({margin_raw * 100:.0f}%) — цену сильно не режем, "
                f"мягкая скидка {suggested}% только чтобы подтянуть спрос. "
                f"Себест. {cost:.0f} ₽ / цена {price:.0f} ₽."
            )
        elif is_low_margin:
            scenario = "low_margin_volume"
            # Постоянные расходы списываем через объём на низкомаржинальных
            if overhead_pressure >= 0.20:
                boost = 5 if overhead_pressure < 0.35 else 8
                suggested = min(30, suggested + boost)
            reason = (
                f"Низкомаржинальная услуга ({margin_raw * 100:.0f}%) — приоритет объёма: "
                f"постоянные затраты ({fixed_month:,.0f} ₽/мес) удобнее закрывать оборотом здесь, "
                f"а высокомаржинальные оставлять без скидки. "
                f"Записей 30д: {bookings} (попул. {popularity:.2f}). "
                f"Себест. {cost:.0f} ₽ / цена {price:.0f} ₽. "
                f"Приоритет {priority:.2f} = объём×0.55 + (1−маржа)×0.45 → скидка {suggested}%."
            )
        else:
            scenario = "volume_fill"
            reason = (
                f"Мало записей ({bookings} за 30д, макс {max_bookings}) — подстегнуть спрос. "
                f"Маржа {margin_raw * 100:.0f}%. Рекомендуемая скидка: {suggested}%."
            )

        # margin_index для хранения: используем «нужность маржи» как 1 - margin для согласованности UI
        rec = ServiceDiscountRecommendation(
            tenant_id=tenant_id,
            service_id=s.id,
            period_days=30,
            bookings_30d=bookings,
            bookings_prev_30d=prev,
            popularity_index=round(popularity, 4),
            margin_raw=round(margin_raw, 4),
            margin_index=round(margin_index, 4),
            priority=round(priority, 4),
            suggested_percent=suggested,
            scenario=scenario,
            reason=reason,
            status="pending",
            computed_at=now,
        )
        db.add(rec)
        created.append(rec)

    await db.commit()
    for r in created:
        await db.refresh(r)
    return created

def _rec_to_out(rec: ServiceDiscountRecommendation) -> ServiceDiscountRecOut:
    svc = rec.service
    price = float(svc.price or 0) if svc else 0
    cost = float(getattr(svc, "cost_price", None) or 0) if svc else 0
    if svc and cost <= 0:
        cost = float(svc.material_cost or 0)
    return ServiceDiscountRecOut(
        id=rec.id,
        service_id=rec.service_id,
        service_name=svc.name if svc else f"Услуга #{rec.service_id}",
        price=price,
        cost_price=cost,
        bookings_30d=rec.bookings_30d,
        bookings_prev_30d=rec.bookings_prev_30d,
        popularity_index=rec.popularity_index,
        margin_raw=rec.margin_raw,
        margin_index=rec.margin_index,
        priority=rec.priority,
        suggested_percent=rec.suggested_percent,
        adjusted_percent=rec.adjusted_percent,
        scenario=rec.scenario,
        reason=rec.reason,
        status=rec.status,
        discount_rule_id=rec.discount_rule_id,
        computed_at=rec.computed_at,
        decided_at=rec.decided_at,
    )

async def _rec_analytics(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ServiceDiscountRecAnalyticsPoint]:
    now = datetime.now(timezone.utc)
    approved = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .options(selectinload(ServiceDiscountRecommendation.service))
            .where(
                ServiceDiscountRecommendation.tenant_id == tenant_id,
                ServiceDiscountRecommendation.status.in_(["approved", "adjusted"]),
                ServiceDiscountRecommendation.decided_at.isnot(None),
            )
            .order_by(ServiceDiscountRecommendation.decided_at.desc())
            .limit(20)
        )
    ).scalars().all()

    out: list[ServiceDiscountRecAnalyticsPoint] = []
    for rec in approved:
        decided = rec.decided_at
        if decided.tzinfo is None:
            decided = decided.replace(tzinfo=timezone.utc)
        before_from = decided - timedelta(days=30)
        after_to = min(now, decided + timedelta(days=30))
        appts = (
            await db.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.service_id == rec.service_id,
                    Appointment.start_time >= before_from,
                    Appointment.start_time <= after_to,
                    Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
                )
            )
        ).scalars().all()
        before_b = after_b = 0
        before_r = after_r = 0.0
        for a in appts:
            if a.start_time < decided:
                before_b += 1
                before_r += float(a.total_price or 0)
            else:
                after_b += 1
                after_r += float(a.total_price or 0)
        growth = ((after_b - before_b) / before_b * 100) if before_b > 0 else (100.0 if after_b else 0.0)
        out.append(ServiceDiscountRecAnalyticsPoint(
            service_id=rec.service_id,
            service_name=rec.service.name if rec.service else f"#{rec.service_id}",
            before_bookings=before_b,
            after_bookings=after_b,
            bookings_growth_percent=round(growth, 1),
            before_revenue=round(before_r, 2),
            after_revenue=round(after_r, 2),
            revenue_delta=round(after_r - before_r, 2),
        ))
    return out

async def _get_client_segment(client_id: int, tenant_id: UUID, db: AsyncSession) -> str:
    """Определить RFM-сегмент клиента."""
    now = datetime.now(timezone.utc)

    # Все завершённые записи клиента
    appts_result = await db.execute(
        select(Appointment).where(
            Appointment.client_id == client_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        ).order_by(Appointment.start_time)
    )
    appts = appts_result.scalars().all()

    freq = len(appts)
    monetary = sum(float(a.total_price or 0) for a in appts)

    recency = 999
    if appts:
        last = max(a.start_time for a in appts)
        recency = (now - last).days if last else 999

    if freq == 0:
        # Клиент без завершённых записей — новый
        return "new"
    elif recency <= 30 and freq > 10 and monetary > 100000:
        return "vip"
    elif recency <= 60 and freq > 5:
        return "loyal"
    elif freq == 1 and recency <= 30:
        return "new"
    elif 60 < recency <= 90:
        return "sleeping"
    elif recency > 90:
        return "lost"
    else:
        return "regular"

async def _auto_apply_discount(appointment_id: int, db: AsyncSession):
    """Автоматически применить скидку к записи (вызывается после создания)."""
    # Загружаем запись со связями
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        print(f"[DEBUG][_auto_apply_discount] Appointment #{appointment_id} not found, skipping.")
        return

    now = datetime.now(timezone.utc)
    tenant_id = appointment.tenant_id

    print(f"[DEBUG][_auto_apply_discount] Appointment #{appointment_id}: "
          f"service_id={appointment.service_id}, "
          f"total_price={appointment.total_price}, "
          f"client_id={appointment.client_id}, "
          f"start_time={appointment.start_time}")

    # Загружаем активные правила скидок (непросроченные)
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            (DiscountRule.valid_until == None) | (DiscountRule.valid_until >= now),
        )
    )
    rules = rules_result.scalars().all()

    print(f"[DEBUG][_auto_apply_discount] Found {len(rules)} active/valid rules for tenant_id={tenant_id}")

    best_discount = 0
    best_rule = None
    weather_day = None
    weather_resolved = False

    async def _weather_for_visit():
        nonlocal weather_day, weather_resolved
        if not weather_resolved:
            from app.modules.discounts.smart import weather_day_for
            weather_day = await weather_day_for(db, tenant_id, appointment.start_time or now)
            weather_resolved = True
        return weather_day

    for rule in rules:
        conditions = rule.conditions or {}
        print(f"[DEBUG][_auto_apply_discount] Checking rule id={rule.id}, name='{rule.name}', "
              f"type={rule.type}, service_id={rule.service_id}, "
              f"discount={rule.discount_percent}%, "
              f"valid_until={rule.valid_until}")

        if rule.type == "happy_hours":
            # Скидка на часовой слот (например, 14:00–16:00)
            if not rule.slot_start or not rule.slot_end:
                continue

            appt_time = appointment.start_time
            if not appt_time:
                continue

            # Извлекаем время записи (часы:минуты)
            appt_slot = appt_time.time()

            # Проверяем, попадает ли время записи в слот
            # Обработка случая, когда слот переходит через полночь (не типично, но на всякий)
            slot_active = False
            if rule.slot_start <= rule.slot_end:
                slot_active = rule.slot_start <= appt_slot <= rule.slot_end
            else:
                # Слот переходит через полночь (например, 22:00–02:00)
                slot_active = appt_slot >= rule.slot_start or appt_slot <= rule.slot_end

            # Дни недели из conditions.weekdays (0=Пн…6=Вс); по умолчанию будни
            allowed_days = conditions.get("weekdays")
            if not isinstance(allowed_days, list) or not allowed_days:
                allowed_days = [0, 1, 2, 3, 4]

            if slot_active and appt_time.weekday() in allowed_days:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "frequency":
            # Скидка за частоту визитов
            min_visits = conditions.get("min_visits", 3)
            # Считаем завершённые записи клиента
            count_result = await db.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.client_id == appointment.client_id,
                    Appointment.tenant_id == tenant_id,
                    Appointment.status == "completed",
                )
            )
            completed_count = count_result.scalar() or 0
            if completed_count >= min_visits:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "win_back":
            from app.modules.discounts.smart import win_back_applies
            if rule.service_id and rule.service_id != appointment.service_id:
                continue
            max_recency_days = conditions.get("max_recency_days", 60)
            last_result = await db.execute(
                select(Appointment.start_time)
                .where(
                    Appointment.client_id == appointment.client_id,
                    Appointment.tenant_id == tenant_id,
                    Appointment.status == "completed",
                )
                .order_by(Appointment.start_time.desc())
                .limit(1)
            )
            last_visit = last_result.scalar()
            if win_back_applies(last_visit, now, max_recency_days):
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "weather":
            from app.modules.discounts.smart import weather_rule_matches
            if rule.service_id and rule.service_id != appointment.service_id:
                continue
            day = await _weather_for_visit()
            if weather_rule_matches(conditions, day):
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "service":
            # Скидка на конкретную услугу
            if rule.service_id and rule.service_id == appointment.service_id:
                print(f"[DEBUG][_auto_apply_discount]  → service MATCH! rule.service_id={rule.service_id} == appointment.service_id={appointment.service_id}")
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule
            else:
                print(f"[DEBUG][_auto_apply_discount]  → service MISMATCH: rule.service_id={rule.service_id} vs appointment.service_id={appointment.service_id}")

        elif rule.type == "client":
            # Персональная скидка для клиента
            if rule.client_id and rule.client_id == appointment.client_id:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "segment":
            # Скидка по RFM-сегменту (например, {"segment": "vip"})
            target_segment = conditions.get("segment", "")
            if target_segment:
                client_seg = await _get_client_segment(appointment.client_id, tenant_id, db)
                if client_seg == target_segment:
                    if rule.discount_percent > best_discount:
                        best_discount = rule.discount_percent
                        best_rule = rule
        elif rule.type == "cashback":
            # Кэшбек начисляется при завершении, не при создании — пропускаем
            continue

    if best_rule and best_discount > 0:
        original_price = float(appointment.total_price)
        # Защита минимальной цены (из conditions: {"min_price": 500})
        raw_conditions = best_rule.conditions or {}
        if isinstance(raw_conditions, str):
            import json
            raw_conditions = json.loads(raw_conditions)
        min_price = float(raw_conditions.get("min_price", 0))
        max_discount = max(0, original_price - min_price)
        effective_discount = min(
            round(original_price * best_discount / 100, 2),
            max_discount,
        )
        appointment.discount_applied = effective_discount
        appointment.total_price = original_price - effective_discount
        cd = ClientDiscount(
            tenant_id=tenant_id,
            client_id=appointment.client_id,
            discount_rule_id=best_rule.id,
            appointment_id=appointment.id,
            applied_percent=best_discount,
            applied_amount=effective_discount,
            is_used=True,
        )
        db.add(cd)
        await db.commit()
        print(f"[DEBUG][_auto_apply_discount] ✓ Applied discount rule #{best_rule.id} '{best_rule.name}': "
              f"{best_discount}% → {effective_discount} руб. "
              f"Price: {original_price} → {appointment.total_price}")
    else:
        print(f"[DEBUG][_auto_apply_discount] ✗ No applicable discount found "
              f"(best_rule={best_rule}, best_discount={best_discount})")

async def _award_loyalty_points(appointment_id: int, db: AsyncSession):
    """Начислить баллы лояльности за завершённую запись."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return

    # Начисляем 1 балл за каждые 100 рублей
    points_to_award = max(1, int(float(appointment.total_price) / 100))

    # Получаем или создаём запись баллов
    points_result = await db.execute(
        select(LoyaltyPoints).where(
            LoyaltyPoints.client_id == appointment.client_id,
            LoyaltyPoints.tenant_id == appointment.tenant_id,
        )
    )
    lp = points_result.scalar_one_or_none()

    if lp:
        lp.balance += points_to_award
        lp.total_earned += points_to_award
    else:
        lp = LoyaltyPoints(
            client_id=appointment.client_id,
            tenant_id=appointment.tenant_id,
            balance=points_to_award,
            total_earned=points_to_award,
            total_spent=0,
        )
        db.add(lp)

    await db.commit()

async def _get_photo_or_404(photo_id: int, db: AsyncSession, tenant_id: UUID) -> Photo:
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.tenant_id == tenant_id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return photo

async def _save_uploaded_photo(
    db: AsyncSession,
    file: UploadFile,
    tenant_id: UUID,
    entity_type: str,
    entity_field: str,
    entity_id: int | None,
    uploaded_by_id: int,
    title: str | None = None,
    service_id: int | None = None,
    description: str | None = None,
) -> PhotoCreateResponse:
    """Validate, save and create Photo record."""
    contents = await file.read()
    mime = validate_image(contents, file.filename or "image.jpg")
    filename = generate_filename(file.filename or "image.jpg")
    subdir = f"{entity_type}s/{entity_id or 'unknown'}"
    url, thumb_url = save_file_local(contents, subdir, filename)

    photo_data = {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "url": url,
        "thumbnail_url": thumb_url,
        "title": title or file.filename,
        "description": description,
        "service_id": service_id,
        "file_size": len(contents),
        "mime_type": mime,
        "uploaded_by_id": uploaded_by_id,
    }
    # entity_field может совпадать с uploaded_by_id (портфолио) — избегаем дубликата
    if entity_field != "uploaded_by_id":
        photo_data[entity_field] = entity_id
    photo = Photo(**photo_data)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return PhotoCreateResponse(
        id=photo.id,
        url=photo.url,
        thumbnail_url=photo.thumbnail_url,
        title=photo.title,
    )

async def recalculate_tier_if_needed(db: AsyncSession, client_id: int, tenant_id: UUID):
    """Пересчитать уровень клиента."""
    from app.services.loyalty_service import recalculate_tier
    await recalculate_tier(db, client_id, tenant_id)

def _parse_date_str(value: str | None):
    """Convert 'YYYY-MM-DD' string to timezone-aware datetime (end of day UTC) or None.

    Ensures the discount remains valid for the entire specified day regardless
    of the server's local timezone offset.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            # Treat as a date-only → end of day UTC so the discount lasts the full day
            dt = dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None

async def _notify_discount_created(db: AsyncSession, rule, admin_user: dict):
    """Send notification about a new discount to relevant clients."""
    from app.core.notification_service import create_notification

    tenant_id = rule.tenant_id
    now = datetime.now(timezone.utc)

    # Собираем получателей
    recipient_ids = []

    if rule.client_id:
        # Персональная скидка — только этому клиенту
        recipient_ids = [rule.client_id]
    elif rule.service_id:
        # Скидка на услугу — всем, кто её заказывал
        appt_result = await db.execute(
            select(Appointment.client_id)
            .where(
                Appointment.service_id == rule.service_id,
                Appointment.tenant_id == tenant_id,
                Appointment.status == "completed",
            )
            .distinct()
        )
        recipient_ids = [r[0] for r in appt_result.all()]
    else:
        # Общая скидка — всем клиентам
        user_result = await db.execute(
            select(User.id).where(
                User.role == "client",
                User.tenant_id == tenant_id,
            )
        )
        recipient_ids = [r[0] for r in user_result.all()]

    # Лимит на число уведомлений (не спамим)
    for uid in recipient_ids[:50]:
        await create_notification(
            db=db,
            user_id=uid,
            tenant_id=tenant_id,
            type="promo",
            channel="in_app",
            title=f"🎉 Новая скидка: {rule.name}",
            message=f"Скидка {rule.discount_percent}% на услуги салона. "
                    f"Действует до {rule.valid_until.strftime('%d.%m.%Y') if rule.valid_until else 'отдельного уведомления'}.",
            related_entity_type="discount",
            related_entity_id=rule.id,
        )


# Star-import must include _helpers used by module routers.
__all__ = [k for k in list(globals()) if not k.startswith("__")]

