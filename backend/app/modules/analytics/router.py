"""HTTP API — модуль analytics."""
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

@router.get("/api/analytics/kpi", response_model=KpiOut)
async def get_kpi(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ключевые показатели для дашборда владельца"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Клиенты
    clients_result = await db.execute(
        select(User).where(
            User.role == "client",
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    total_clients = len(clients_result.scalars().all())

    # Мастера
    masters_result = await db.execute(
        select(User).where(
            User.role == "master",
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    total_masters = len(masters_result.scalars().all())

    # Записи сегодня
    today_result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= today_start,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    today_appts = today_result.scalars().all()

    # Записи за месяц
    month_result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    month_appts = month_result.scalars().all()

    # Выручка
    today_revenue = sum(
        float(a.total_price or 0) for a in today_appts if a.status == "completed"
    )
    month_revenue = sum(
        float(a.total_price or 0) for a in month_appts if a.status == "completed"
    )

    # Ожидающие
    pending_result = await db.execute(
        select(Appointment).where(
            Appointment.status == "pending",
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    pending_count = len(pending_result.scalars().all())

    from app.modules.analytics.spec import sparkline_series
    from app.modules.appointments.live_service import build_live_floor

    tenant_id = UUID(current_user["tenant_id"])
    spark_rev, spark_n, spark_done = await sparkline_series(db, tenant_id)

    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    prev_week_start = week_start - timedelta(days=7)
    week_rows = (
        await db.execute(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.status == "completed",
                Appointment.start_time >= prev_week_start,
            )
        )
    ).scalars().all()
    def _aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    week_revenue = sum(
        float(a.total_price or 0)
        for a in week_rows
        if _aware(a.start_time) and _aware(a.start_time) >= week_start
    )
    prev_week_revenue = sum(
        float(a.total_price or 0)
        for a in week_rows
        if _aware(a.start_time) and prev_week_start <= _aware(a.start_time) < week_start
    )
    week_change = (
        round((week_revenue - prev_week_revenue) / prev_week_revenue * 100, 1)
        if prev_week_revenue
        else 0.0
    )

    live = await build_live_floor(db, tenant_id)
    active_boxes = [b for b in live.get("boxes", []) if b.get("is_active")]
    busy = [b for b in active_boxes if b.get("state") in ("occupied", "preparing", "booked")]
    occupancy_pct = round((len(busy) / len(active_boxes) * 100), 1) if active_boxes else 0.0

    return KpiOut(
        total_clients=total_clients,
        total_masters=total_masters,
        today_appointments=len(today_appts),
        today_revenue=today_revenue,
        month_revenue=month_revenue,
        pending_appointments=pending_count,
        completed_month=sum(1 for a in month_appts if a.status == "completed"),
        sparkline_revenue=spark_rev,
        sparkline_appointments=spark_n,
        sparkline_completed=spark_done,
        occupancy_pct=occupancy_pct,
        week_revenue=round(week_revenue, 2),
        week_change_percent=week_change,
    )


@router.get("/api/analytics/spec", response_model=AnalyticsSpecResponse)
async def get_analytics_spec(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Когорты, treemap услуг, загрузка мастеров и боксов."""
    from app.modules.analytics.spec import build_spec

    return await build_spec(db, UUID(current_user["tenant_id"]))

@router.get("/api/analytics/expenses", response_model=ExpenseAnalyticsResponse)
async def get_expense_analytics(
    months: int = Query(6, ge=1, le=24),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика затрат: разбивка, графики, ИИ-подсказки."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = (now.replace(day=1) - timedelta(days=months * 31)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.tenant_id == tenant_id,
                Expense.expense_date >= date_from,
            )
        )
    ).scalars().all()

    total = sum(float(e.amount or 0) for e in expenses)
    paid_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", "paid") or "paid") == "paid")
    unpaid_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", None) or "") == "unpaid")
    overdue_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", None) or "") == "overdue")

    cat_map: dict[str, dict] = {}
    for e in expenses:
        cat = e.category or "other"
        if cat not in cat_map:
            cat_map[cat] = {"amount": 0.0, "count": 0}
        cat_map[cat]["amount"] += float(e.amount or 0)
        cat_map[cat]["count"] += 1

    by_category = [
        ExpenseCategoryBreakdown(
            category=k,
            label=EXPENSE_CAT_LABELS.get(k, k),
            amount=round(v["amount"], 2),
            share_percent=round((v["amount"] / total * 100) if total else 0, 1),
            count=v["count"],
        )
        for k, v in sorted(cat_map.items(), key=lambda x: x[1]["amount"], reverse=True)
    ]

    # by month
    month_map: dict[str, dict] = {}
    for e in expenses:
        if not e.expense_date:
            continue
        key = e.expense_date.strftime("%Y-%m")
        if key not in month_map:
            month_map[key] = {"total": 0.0, "by_category": {}}
        month_map[key]["total"] += float(e.amount or 0)
        cat = e.category or "other"
        month_map[key]["by_category"][cat] = month_map[key]["by_category"].get(cat, 0) + float(e.amount or 0)

    month_names = {
        1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
        7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
    }
    by_month = []
    for key in sorted(month_map.keys()):
        y, m = key.split("-")
        by_month.append(ExpenseMonthPoint(
            month=key,
            label=f"{month_names[int(m)]} {y}",
            total=round(month_map[key]["total"], 2),
            by_category={k: round(v, 2) for k, v in month_map[key]["by_category"].items()},
        ))

    # Revenue this month for break-even / forecast
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    appts = (
        await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.invoice),
            )
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= month_start,
                Appointment.status == "completed",
            )
        )
    ).scalars().all()
    from app.modules.appointments.close_service import snapshot_material_cost, snapshot_revenue
    revenue_month = sum(snapshot_revenue(a) for a in appts)
    material_month = sum(snapshot_material_cost(a) for a in appts)

    # Fixed costs this month
    month_expenses = [e for e in expenses if e.expense_date and e.expense_date >= month_start]
    fixed_month = sum(float(e.amount or 0) for e in month_expenses)

    # Contribution margin ratio
    from app.finance_formulas import contribution_ratio, break_even_revenue, forecast_profit as calc_forecast_profit
    contrib_ratio = contribution_ratio(revenue_month, material_month)
    break_even = break_even_revenue(fixed_month, contrib_ratio)
    forecast_profit = calc_forecast_profit(revenue_month, material_month, fixed_month)

    insights: list[ExpenseInsight] = []

    # MoM anomalies by category
    if len(by_month) >= 2:
        prev, cur = by_month[-2], by_month[-1]
        for cat_key, label in EXPENSE_CAT_LABELS.items():
            prev_v = prev.by_category.get(cat_key, 0)
            cur_v = cur.by_category.get(cat_key, 0)
            if prev_v > 0 and cur_v > prev_v * 1.3:
                growth = (cur_v - prev_v) / prev_v * 100
                insights.append(ExpenseInsight(
                    type="anomaly",
                    severity="critical" if growth >= 40 else "warn",
                    title=f"Рост: {label}",
                    message=f"{label} выросли на {growth:.0f}% ({prev_v:,.0f} → {cur_v:,.0f} ₽). Проверьте счета и тарифы.",
                ))

    # Rent share tip
    rent = cat_map.get("rent", {}).get("amount", 0)
    if revenue_month > 0 and rent > 0:
        # approximate monthly rent from period share
        rent_month = sum(float(e.amount or 0) for e in month_expenses if e.category == "rent")
        share = rent_month / revenue_month * 100
        if share >= 25:
            insights.append(ExpenseInsight(
                type="tip",
                severity="warn",
                title="Аренда дорогая относительно выручки",
                message=f"Аренда ≈ {share:.0f}% выручки месяца. Ориентир для салона — до 15–20%. Рассмотрите пересмотр договора или рост загрузки.",
            ))

    # Marketing efficiency
    mkt_month = sum(float(e.amount or 0) for e in month_expenses if e.category == "marketing")
    if mkt_month > 0 and revenue_month > 0:
        roi_proxy = revenue_month / mkt_month
        if roi_proxy < 5:
            insights.append(ExpenseInsight(
                type="tip",
                severity="warn",
                title="Реклама может быть неэффективна",
                message=f"На 1 ₽ рекламы приходится ≈ {roi_proxy:.1f} ₽ выручки. Проверьте каналы: отключите слабые, усильте рабочие.",
            ))
        elif roi_proxy >= 10:
            insights.append(ExpenseInsight(
                type="tip",
                severity="info",
                title="Реклама работает",
                message=f"Соотношение выручка/реклама ≈ {roi_proxy:.1f}× — можно аккуратно масштабировать рабочие каналы.",
            ))

    insights.append(ExpenseInsight(
        type="break_even",
        severity="info",
        title="Точка безубыточности",
        message=(
            f"При текущих постоянных затратах ({fixed_month:,.0f} ₽) и марже после материалов "
            f"нужна выручка ≈ {break_even:,.0f} ₽/мес. Сейчас: {revenue_month:,.0f} ₽."
        ),
    ))
    insights.append(ExpenseInsight(
        type="forecast",
        severity="info" if forecast_profit >= 0 else "warn",
        title="Прогноз прибыли (месяц)",
        message=f"Выручка − материалы − постоянные ≈ {forecast_profit:,.0f} ₽.",
    ))

    return ExpenseAnalyticsResponse(
        total=round(total, 2),
        paid_total=round(paid_total, 2),
        unpaid_total=round(unpaid_total, 2),
        overdue_total=round(overdue_total, 2),
        by_category=by_category,
        by_month=by_month,
        insights=insights,
        break_even_revenue=break_even,
        forecast_profit=forecast_profit,
        revenue_month=round(revenue_month, 2),
    )

@router.get("/api/analytics/pl", response_model=PLReport)
async def get_pl_report(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """P&L отчёт: прибыли и убытки + маржинальность услуг."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Выручка ---
    month_appts = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.service),
            selectinload(Appointment.box),
            selectinload(Appointment.invoice).selectinload(AppointmentInvoice.box),
        )
        .where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    appts = month_appts.scalars().all()
    completed = [a for a in appts if a.status == "completed"]

    from app.finance_formulas import (
        avg_check as calc_avg_check,
        gross_margin_percent,
        gross_profit as calc_gross_profit,
        net_margin_percent,
        net_profit as calc_net_profit,
    )
    from app.modules.appointments.close_service import (
        compute_box_margins,
        snapshot_material_cost,
        snapshot_revenue,
    )

    total_revenue = sum(snapshot_revenue(a) for a in completed)
    completed_count = len(completed)
    avg_check = calc_avg_check(total_revenue, completed_count)

    # --- Материальные затраты (чек закрытия, иначе каталог) ---
    total_material_cost = sum(snapshot_material_cost(a) for a in completed)

    # --- Маржинальность по услугам ---
    service_map: dict[int, dict] = {}
    for a in completed:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_map:
            srv = a.service
            service_map[sid] = {
                "service_id": sid,
                "service_name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "total_revenue": 0.0,
                "total_material_cost": 0.0,
                "appointment_count": 0,
            }
        service_map[sid]["total_revenue"] += snapshot_revenue(a)
        service_map[sid]["total_material_cost"] += snapshot_material_cost(a)
        service_map[sid]["appointment_count"] += 1

    service_margins = []
    for s in service_map.values():
        gp = s["total_revenue"] - s["total_material_cost"]
        mp = round(gp / s["total_revenue"] * 100, 1) if s["total_revenue"] else 0
        service_margins.append(ServiceMargin(
            service_id=s["service_id"],
            service_name=s["service_name"],
            category=s["category"],
            total_revenue=round(s["total_revenue"], 2),
            total_material_cost=round(s["total_material_cost"], 2),
            gross_profit=round(gp, 2),
            margin_percent=mp,
            appointment_count=s["appointment_count"],
        ))
    service_margins.sort(key=lambda x: x.appointment_count, reverse=True)

    # --- Постоянные расходы ---
    expenses_result = await db.execute(
        select(Expense).where(
            Expense.tenant_id == tenant_id,
            Expense.expense_date >= month_start,
        )
    )
    expenses = expenses_result.scalars().all()
    total_expenses = sum(float(e.amount or 0) for e in expenses)

    expenses_by_category: dict[str, float] = {}
    for e in expenses:
        cat = e.category or "other"
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + float(e.amount or 0)

    # --- Итоговые расчёты ---
    gross_profit = calc_gross_profit(total_revenue, total_material_cost)
    gross_margin = gross_margin_percent(total_revenue, total_material_cost)
    net_profit = calc_net_profit(total_revenue, total_material_cost, total_expenses)
    net_margin = net_margin_percent(total_revenue, total_material_cost, total_expenses)

    return PLReport(
        total_revenue=round(total_revenue, 2),
        completed_appointments=completed_count,
        avg_check=avg_check,
        total_material_cost=round(total_material_cost, 2),
        total_expenses=round(total_expenses, 2),
        expenses_by_category=expenses_by_category,
        gross_profit=gross_profit,
        gross_margin_percent=gross_margin,
        net_profit=net_profit,
        net_margin_percent=net_margin,
        service_margins=service_margins,
        box_margins=[BoxMargin(**row) for row in compute_box_margins(completed, total_expenses)],
        period="month",
    )

@router.get("/api/analytics/box-margins", response_model=list[BoxMargin])
async def get_box_margins_report(
    period: str = Query("month", pattern="^(day|week|month)$", description="Период: day/week/month"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Маржинальность по боксам за период (аналог box_margins из P&L, но с периодом)."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    days = {"day": 1, "week": 7, "month": 30}[period]
    start = now - timedelta(days=days)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    from app.modules.appointments.close_service import compute_box_margins

    appts_result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.service),
            selectinload(Appointment.box),
            selectinload(Appointment.invoice).selectinload(AppointmentInvoice.box),
        )
        .where(
            Appointment.start_time >= start,
            Appointment.status == "completed",
            Appointment.tenant_id == tenant_id,
        )
    )
    completed = appts_result.scalars().all()

    expenses_result = await db.execute(
        select(Expense).where(
            Expense.tenant_id == tenant_id,
            Expense.expense_date >= start,
        )
    )
    total_expenses = sum(float(e.amount or 0) for e in expenses_result.scalars().all())

    rows = compute_box_margins(completed, total_expenses)
    return [BoxMargin(**row) for row in rows]

@router.get("/api/analytics/revenue", response_model=RevenueResponse)
async def get_revenue_chart(
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Дневная выручка за период (Area Chart) + сравнение с предыдущим периодом."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем границы периода
    if start_date and end_date:
        s_date = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        e_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        # По умолчанию — текущий месяц
        s_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if s_date.month == 12:
            e_date = s_date.replace(year=s_date.year + 1, month=1)
        else:
            e_date = s_date.replace(month=s_date.month + 1)

    period_days = (e_date - s_date).days

    # Предыдущий период (такой же длины)
    prev_end = s_date
    prev_start = prev_end - timedelta(days=period_days)

    async def _fetch_period(start: datetime, end: datetime) -> tuple[list[RevenuePoint], float, float]:
        """Вспомогательная функция: получить данные за период."""
        result = await db.execute(
            select(Appointment).where(
                Appointment.start_time >= start,
                Appointment.start_time < end,
                Appointment.tenant_id == tenant_id,
                Appointment.status == "completed",
            ).order_by(Appointment.start_time)
        )
        appts = result.scalars().all()

        # Если период <= 31 день — группировка по дням, иначе по неделям/месяцам
        daily: dict[str, dict] = {}
        for a in appts:
            if period_days <= 35:
                key = a.start_time.strftime("%Y-%m-%d")
            else:
                key = a.start_time.strftime("%Y-%m-%d")  # пока дни, фронт сам сгруппирует
            if key not in daily:
                daily[key] = {"revenue": 0.0, "appointments": 0}
            daily[key]["revenue"] += float(a.total_price or 0)
            daily[key]["appointments"] += 1

        points = [
            RevenuePoint(date=key, revenue=round(v["revenue"], 2), appointments=v["appointments"])
            for key, v in sorted(daily.items())
        ]
        total = round(sum(p.revenue for p in points), 2)
        days_count = max(len(daily), 1)
        avg = round(total / days_count, 2) if days_count else 0
        return points, total, avg

    # Основной период
    points, total, avg = await _fetch_period(s_date, e_date)

    # Предыдущий период
    prev_points, prev_total, prev_avg = await _fetch_period(prev_start, prev_end)

    # Лучший/худший день
    days_with_data = [p for p in points if p.appointments > 0]
    best = max(days_with_data, key=lambda p: p.revenue) if days_with_data else None
    worst = min(days_with_data, key=lambda p: p.revenue) if days_with_data else None

    # Изменение в %
    change_percent = round(
        ((total - prev_total) / prev_total * 100) if prev_total else 0, 1
    )

    return RevenueResponse(
        daily=points,
        total=total,
        avg_per_day=avg,
        best_day=best.date if best else None,
        worst_day=worst.date if worst else None,
        previous_total=round(prev_total, 2),
        change_percent=change_percent,
        previous_avg_per_day=prev_avg,
    )

@router.get("/api/analytics/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    box_id: int | None = Query(None, description="Фильтр по боксу"),
    days: int = Query(60, ge=7, le=120, description="Период анализа в днях"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Тепловая карта загрузки: день недели × час за выбранный период."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(days=days)

    # Фильтр по боксу
    filters = [
        Appointment.start_time >= date_from,
        Appointment.start_time <= now,
        Appointment.tenant_id == tenant_id,
        Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
    ]
    if box_id is not None:
        filters.append(Appointment.box_id == box_id)

    result = await db.execute(
        select(Appointment).where(*filters)
    )
    appts = result.scalars().all()

    # Сетка 7×15 (дни недели × часы 8-22)
    cells_map: dict[tuple[int, int], dict] = {}
    for day in range(7):
        for hour in range(8, 23):
            cells_map[(day, hour)] = {"count": 0, "revenue": 0.0}

    for a in appts:
        day = a.start_time.weekday()  # 0=Mon
        hour = a.start_time.hour
        key = (day, hour)
        if key in cells_map:
            cells_map[key]["count"] += 1
            cells_map[key]["revenue"] += float(a.total_price or 0)

    cells = [
        HeatmapCell(
            day=d, hour=h, count=v["count"],
            revenue=round(v["revenue"], 2),
            box_id=box_id,
        )
        for (d, h), v in sorted(cells_map.items())
    ]

    # Загружаем список боксов тенанта
    boxes_result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id).order_by(Box.sort_order, Box.name)
    )
    boxes = boxes_result.scalars().all()

    # Загружаем привязки услуг для всех боксов (как в /api/boxes)
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

    return HeatmapResponse(cells=cells, boxes=out)

@router.get("/api/analytics/funnel", response_model=FunnelResponse)
async def get_funnel(
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Воронка продаж: конверсия по статусам за период (по дате создания записи)."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем границы периода по created_at
    if start_date and end_date:
        date_from = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_to = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        # По умолчанию — последние 30 дней
        date_to = now
        date_from = date_to - timedelta(days=30)

    result = await db.execute(
        select(Appointment).where(
            Appointment.created_at >= date_from,
            Appointment.created_at <= date_to,
            Appointment.tenant_id == tenant_id,
        )
    )
    appts = result.scalars().all()

    total = len(appts)
    status_order = ["pending", "confirmed", "in_progress", "completed", "cancelled", "no_show"]
    counts = {s: 0 for s in status_order}
    for a in appts:
        s = a.status or "pending"
        if s in counts:
            counts[s] += 1

    funnel_stages = ["pending", "confirmed", "in_progress", "completed"]
    stage_labels = {
        "pending": "Создано",
        "confirmed": "Подтверждено",
        "in_progress": "В работе",
        "completed": "Выполнено",
    }
    stage_colors = {
        "pending": "#C8A977",
        "confirmed": "#4ECB71",
        "in_progress": "#AAB2BF",
        "completed": "#C8A977",
    }

    stages = []
    for i, s in enumerate(funnel_stages):
        val = counts[s]
        pct = round(val / total * 100, 1) if total else 0
        stages.append(FunnelStage(
            name=stage_labels[s],
            value=val,
            percent=pct,
            color=stage_colors[s],
        ))

    conversion = round(counts["completed"] / total * 100, 1) if total else 0

    return FunnelResponse(
        stages=stages,
        total=total,
        conversion_rate=conversion,
    )

@router.get("/api/analytics/discounts", response_model=DiscountAnalyticsResponse)
async def get_discount_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика эффективности скидок."""
    tenant_id = UUID(current_user["tenant_id"])

    # Все правила
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    all_rules = rules_result.scalars().all()
    total_rules = len(all_rules)
    active_rules = sum(1 for r in all_rules if r.is_active)

    # Все применения скидок
    cd_result = await db.execute(
        select(ClientDiscount)
        .options(selectinload(ClientDiscount.discount_rule))
        .where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    all_cd = cd_result.scalars().all()

    total_times_used = len(all_cd)
    total_discount_amount = sum(float(cd.applied_amount or 0) for cd in all_cd)
    unique_clients = len(set(cd.client_id for cd in all_cd))

    # Топ правил по использованию
    rule_usage: dict[int, dict] = {}
    for cd in all_cd:
        rid = cd.discount_rule_id
        if rid not in rule_usage:
            rule_usage[rid] = {"times_used": 0, "total_discount": 0.0, "clients": set()}
        rule_usage[rid]["times_used"] += 1
        rule_usage[rid]["total_discount"] += float(cd.applied_amount or 0)
        rule_usage[rid]["clients"].add(cd.client_id)

    top_rules = []
    for rid, stats in sorted(rule_usage.items(), key=lambda x: x[1]["times_used"], reverse=True)[:10]:
        rule = next((r for r in all_rules if r.id == rid), None)
        top_rules.append(DiscountAnalyticsTopRule(
            rule_id=rid,
            rule_name=rule.name if rule else f"Правило #{rid}",
            rule_type=rule.type if rule else "unknown",
            times_used=stats["times_used"],
            total_discount=round(stats["total_discount"], 2),
            client_count=len(stats["clients"]),
        ))

    return DiscountAnalyticsResponse(
        total_rules=total_rules,
        active_rules=active_rules,
        total_times_used=total_times_used,
        total_discount_amount=round(total_discount_amount, 2),
        unique_clients_affected=unique_clients,
        top_rules=top_rules,
    )

@router.get("/api/analytics/discount-intelligence", response_model=DiscountIntelligenceResponse)
async def get_discount_intelligence(
    days: int = Query(60, ge=14, le=120, description="Период анализа"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка → авто-предложения Happy Hours + ROI + рекомендации."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(days=days)

    result = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= date_from,
            Appointment.start_time <= now,
            Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
        )
    )
    appts = result.scalars().all()

    # Сколько раз встречался каждый weekday в периоде
    weekday_occ: dict[int, int] = {d: 0 for d in range(7)}
    cursor = date_from.date()
    end_d = now.date()
    while cursor <= end_d:
        weekday_occ[cursor.weekday()] += 1
        cursor += timedelta(days=1)

    cells_map: dict[tuple[int, int], dict] = {}
    for day in range(7):
        for hour in range(8, 23):
            cells_map[(day, hour)] = {"count": 0, "revenue": 0.0}

    for a in appts:
        key = (a.start_time.weekday(), a.start_time.hour)
        if key in cells_map:
            cells_map[key]["count"] += 1
            cells_map[key]["revenue"] += float(a.total_price or 0)

    cells = [
        HeatmapCell(day=d, hour=h, count=v["count"], revenue=round(v["revenue"], 2))
        for (d, h), v in sorted(cells_map.items())
    ]

    def avg_for(day: int, hour: int) -> float:
        occ = max(weekday_occ.get(day, 1), 1)
        return cells_map[(day, hour)]["count"] / occ

    # Группы: Пн–Пт и Сб / Вс отдельно (Вс тоже)
    groups = [
        ([0, 1, 2, 3, 4], "Пн–Пт", "wd"),
        ([5], "Сб", "sat"),
        ([6], "Вс", "sun"),
    ]

    suggestions: list[DiscountSuggestion] = []
    for weekdays, label, prefix in groups:
        hour_percents = _build_group_hour_percents(weekdays, avg_for)
        suggestions.extend(_merge_hour_suggestions(hour_percents, weekdays, label, prefix))

    # Существующие правила
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    all_rules = rules_result.scalars().all()

    cd_result = await db.execute(
        select(ClientDiscount).where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    all_cd = cd_result.scalars().all()
    usage_by_rule: dict[int, list] = defaultdict(list)
    for cd in all_cd:
        usage_by_rule[cd.discount_rule_id].append(cd)

    avg_check = 0.0
    completed = [a for a in appts if a.status == "completed"]
    if completed:
        avg_check = sum(float(a.total_price or 0) for a in completed) / len(completed)

    roi: list[DiscountRoiItem] = []
    before_after: list[DiscountBeforeAfterPoint] = []
    recommendations: list[DiscountRuleAdvice] = []

    for rule in all_rules:
        used = usage_by_rule.get(rule.id, [])
        cost = sum(float(cd.applied_amount or 0) for cd in used)
        times = len(used)
        from app.finance_formulas import discount_roi
        roi_calc = discount_roi(times, cost, avg_check)
        roi.append(DiscountRoiItem(
            rule_id=rule.id,
            rule_name=rule.name,
            times_used=times,
            discount_cost=round(cost, 2),
            estimated_extra_revenue=roi_calc["estimated_extra_revenue"],
            roi_percent=roi_calc["roi_percent"],
            verdict=roi_calc["verdict"],
        ))

        if rule.type == "happy_hours" and rule.slot_start and rule.slot_end:
            h0 = rule.slot_start.hour
            h1 = rule.slot_end.hour
            if h1 <= h0:
                h1 = h0 + 1
            cond_days = (rule.conditions or {}).get("weekdays")
            if not isinstance(cond_days, list) or not cond_days:
                cond_days = list(range(5))  # legacy: будни

            created = rule.created_at or date_from
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            before_from = created - timedelta(days=30)
            after_to = min(now, created + timedelta(days=30))

            def slot_avg(a_from, a_to):
                cnt = 0
                days_n = 0
                d = a_from.date()
                while d <= a_to.date():
                    if d.weekday() in cond_days:
                        days_n += 1
                    d += timedelta(days=1)
                for a in appts:
                    if a_from <= a.start_time <= a_to and a.start_time.weekday() in cond_days:
                        if h0 <= a.start_time.hour < h1:
                            cnt += 1
                return round(cnt / max(days_n, 1), 2)

            # для before/after нужны все записи — подгрузим расширенный диапазон
            before_avg = 0.0
            after_avg = 0.0
            ext = await db.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.start_time >= before_from,
                    Appointment.start_time <= after_to,
                    Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
                )
            )
            ext_appts = ext.scalars().all()

            def slot_avg_ext(a_from, a_to, pool):
                cnt = 0
                days_n = 0
                d = a_from.date()
                while d <= a_to.date():
                    if d.weekday() in cond_days:
                        days_n += 1
                    d += timedelta(days=1)
                for a in pool:
                    if a_from <= a.start_time <= a_to and a.start_time.weekday() in cond_days:
                        if h0 <= a.start_time.hour < h1:
                            cnt += 1
                return round(cnt / max(days_n, 1), 2)

            before_avg = slot_avg_ext(before_from, created, ext_appts)
            after_avg = slot_avg_ext(created, after_to, ext_appts)
            before_after.append(DiscountBeforeAfterPoint(
                rule_id=rule.id,
                rule_name=rule.name,
                label=f"{rule.slot_start.strftime('%H:%M')}–{rule.slot_end.strftime('%H:%M')}",
                before_avg=before_avg,
                after_avg=after_avg,
            ))

            # Рекомендация: относительно пика группы; широкий слот с пиком внутри — отключить
            peak_for_rule = max(
                (avg_for(d, h) for d in cond_days for h in range(8, 23)),
                default=0.0,
            )
            hour_ideals: list[int] = []
            hour_loads: list[float] = []
            for h in range(h0, min(h1, 23)):
                load = max((avg_for(d, h) for d in cond_days), default=0.0)
                hour_loads.append(load)
                hour_ideals.append(_discount_percent_relative(load, peak_for_rule))
            slot_avg_now = sum(hour_loads) / len(hour_loads) if hour_loads else 0.0
            peak_hours_inside = sum(1 for p in hour_ideals if p == 0)
            idle_ideals = [p for p in hour_ideals if p > 0]
            if peak_hours_inside > 0:
                ideal = 0
            elif idle_ideals:
                ideal = min(idle_ideals)
            else:
                ideal = _discount_percent_relative(slot_avg_now, peak_for_rule)

            if not rule.is_active:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="keep",
                    message="Правило выключено",
                ))
            elif peak_hours_inside > 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=(
                        f"Слот {h0:02d}:00–{h1:02d}:00 перекрывает пик загрузки "
                        f"({peak_hours_inside} ч). На пике скидку давать нельзя — "
                        f"сузьте до пустых часов или отключите."
                    ),
                    suggested_percent=0,
                ))
            elif ideal == 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=f"Слот у пика (ср. {slot_avg_now:.2f}) — скидку лучше отключить",
                    suggested_percent=0,
                ))
            elif ideal > rule.discount_percent + 4:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="increase",
                    message=f"Слот пустой (ср. {slot_avg_now:.2f}) — увеличить до {ideal}%",
                    suggested_percent=ideal,
                ))
            elif ideal < rule.discount_percent - 4:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="decrease",
                    message=f"Загрузка выросла (ср. {slot_avg_now:.2f}) — снизить до {ideal}%",
                    suggested_percent=ideal,
                ))
            elif verdict == "отключить" and times > 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=f"ROI {roi_pct}% отрицательный — отключить или пересобрать слот",
                ))
            else:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="keep",
                    message=f"Слот ок (ср. {slot_avg_now:.2f}, ROI {roi_pct}%)",
                    suggested_percent=rule.discount_percent,
                ))

    # Предложения, которых ещё нет как правил
    existing_keys = set()
    for r in all_rules:
        if r.type == "happy_hours" and r.slot_start and r.slot_end:
            existing_keys.add(
                (r.slot_start.strftime("%H:%M"), r.slot_end.strftime("%H:%M"), r.discount_percent)
            )

    for s in suggestions:
        if (s.hour_start, s.hour_end, s.discount_percent) not in existing_keys:
            recommendations.insert(0, DiscountRuleAdvice(
                rule_id=None,
                rule_name=s.name,
                action="create",
                message=s.reason,
                suggested_percent=s.discount_percent,
            ))

    return DiscountIntelligenceResponse(
        period_days=days,
        cells=cells,
        suggestions=suggestions,
        recommendations=recommendations[:20],
        roi=roi,
        before_after=before_after,
    )

@router.get("/api/analytics/service-discount-recs", response_model=ServiceDiscountRecsResponse)
async def get_service_discount_recs(
    force: bool = Query(False, description="Принудительный пересчёт"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Рекомендации скидок по услугам. Авто-обновление раз в неделю."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    auto_refreshed = False

    latest = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
            .order_by(ServiceDiscountRecommendation.computed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    need_refresh = force or latest is None
    if latest and latest.computed_at:
        computed = latest.computed_at
        if computed.tzinfo is None:
            computed = computed.replace(tzinfo=timezone.utc)
        if now - computed >= timedelta(days=7):
            need_refresh = True

    if need_refresh:
        await _compute_service_discount_recs(db, tenant_id)
        auto_refreshed = True
        latest = (
            await db.execute(
                select(ServiceDiscountRecommendation)
                .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
                .order_by(ServiceDiscountRecommendation.computed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    rows = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .options(selectinload(ServiceDiscountRecommendation.service))
            .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
            .order_by(
                ServiceDiscountRecommendation.status.asc(),
                ServiceDiscountRecommendation.priority.desc(),
            )
        )
    ).scalars().all()

    last_at = latest.computed_at if latest else None
    next_at = (last_at + timedelta(days=7)) if last_at else now
    analytics = await _rec_analytics(db, tenant_id)

    return ServiceDiscountRecsResponse(
        last_computed_at=last_at,
        next_refresh_at=next_at,
        auto_refreshed=auto_refreshed,
        items=[_rec_to_out(r) for r in rows],
        analytics=analytics,
    )

@router.post("/api/analytics/service-discount-recs/refresh", response_model=ServiceDiscountRecsResponse)
async def refresh_service_discount_recs(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Принудительный пересчёт рекомендаций."""
    return await get_service_discount_recs(force=True, current_user=current_user, db=db)

@router.post("/api/analytics/service-discount-recs/{rec_id}/decide", response_model=ServiceDiscountRecOut)
async def decide_service_discount_rec(
    rec_id: int,
    body: ServiceDiscountRecDecision,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Утвердить / отклонить / скорректировать рекомендацию."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(ServiceDiscountRecommendation)
        .options(selectinload(ServiceDiscountRecommendation.service))
        .where(
            ServiceDiscountRecommendation.id == rec_id,
            ServiceDiscountRecommendation.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    if rec.status not in ("pending",):
        raise HTTPException(status_code=400, detail="Рекомендация уже обработана")

    action = (body.action or "").lower().strip()
    now = datetime.now(timezone.utc)

    if action == "reject":
        rec.status = "rejected"
        rec.decided_at = now
        await db.commit()
        await db.refresh(rec)
        return _rec_to_out(rec)

    if action not in ("approve", "adjust"):
        raise HTTPException(status_code=400, detail="action: approve | reject | adjust")

    percent = body.adjusted_percent if action == "adjust" and body.adjusted_percent else rec.suggested_percent
    if action == "adjust":
        if not body.adjusted_percent:
            raise HTTPException(status_code=400, detail="Укажите adjusted_percent")
        rec.adjusted_percent = percent
        rec.status = "adjusted"
    else:
        rec.status = "approved"

    svc_name = rec.service.name if rec.service else f"Услуга #{rec.service_id}"
    rule_name = f"Скидка на услугу: {svc_name} (−{percent}%)"
    # уникальное имя
    exists = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id, DiscountRule.name == rule_name)
    )
    if exists.scalar_one_or_none():
        rule_name = f"{rule_name} · {now.strftime('%d.%m')}"

    rule = DiscountRule(
        name=rule_name,
        type="service",
        conditions={
            "source": "service_margin_rec",
            "rec_id": rec.id,
            "priority": rec.priority,
            "scenario": rec.scenario,
        },
        discount_percent=percent,
        service_id=rec.service_id,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(rule)
    await db.flush()
    rec.discount_rule_id = rule.id
    rec.decided_at = now
    await db.commit()

    result = await db.execute(
        select(ServiceDiscountRecommendation)
        .options(selectinload(ServiceDiscountRecommendation.service))
        .where(ServiceDiscountRecommendation.id == rec.id)
    )
    rec = result.scalar_one()
    return _rec_to_out(rec)

@router.get("/api/analytics/services", response_model=ServiceAnalyticsResponse)
async def get_service_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
):
    """Аналитика по услугам: тренды, сравнение, топ-5, прогноз."""
    from collections import defaultdict
    from datetime import datetime, timezone, timedelta
    import math

    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем периоды
    current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_start = (current_start - timedelta(days=1)).replace(day=1)
    prev_prev_start = (previous_start - timedelta(days=1)).replace(day=1)

    # Все услуги тенанта
    services_result = await db.execute(
        select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
    )
    services = {s.id: s for s in services_result.scalars().all()}

    # Все завершённые записи за период
    start_date = now - timedelta(days=months * 31)
    appts_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service))
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= start_date,
        )
        .order_by(Appointment.start_time)
    )
    appts = appts_result.scalars().all()

    # --- 1. Тренды по месяцам ---
    monthly_data: dict[int, dict[str, dict]] = {}
    for a in appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in monthly_data:
            monthly_data[sid] = {}
        month_key = a.start_time.strftime("%Y-%m")
        if month_key not in monthly_data[sid]:
            monthly_data[sid][month_key] = {"revenue": 0.0, "count": 0}
        monthly_data[sid][month_key]["revenue"] += float(a.total_price or 0)
        monthly_data[sid][month_key]["count"] += 1

    trends = []
    for sid, months_data in monthly_data.items():
        srv = services.get(sid)
        monthly = [
            ServiceTrendPoint(month=m, revenue=round(d["revenue"], 2), count=d["count"])
            for m, d in sorted(months_data.items())
        ]
        trends.append(ServiceTrend(
            service_id=sid,
            service_name=srv.name if srv else f"Услуга #{sid}",
            category=srv.category if srv else None,
            monthly=monthly,
        ))

    # --- 2. Сравнение периодов ---
    comparison = []
    for sid in monthly_data:
        srv = services.get(sid)
        prev_month = previous_start.strftime("%Y-%m")
        prev_prev = prev_prev_start.strftime("%Y-%m")

        cur = monthly_data[sid].get(prev_month, {"revenue": 0.0, "count": 0})
        prev = monthly_data[sid].get(prev_prev, {"revenue": 0.0, "count": 0})

        change = 0.0
        if prev["revenue"] > 0:
            change = round((cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100, 1)

        comparison.append(ServiceComparison(
            service_id=sid,
            service_name=srv.name if srv else f"Услуга #{sid}",
            current_revenue=round(cur["revenue"], 2),
            previous_revenue=round(prev["revenue"], 2),
            change_percent=change,
            current_count=cur["count"],
            previous_count=prev["count"],
        ))

    # --- 3. Топ-5 услуг ---
    service_totals: dict[int, dict] = {}
    for a in appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_totals:
            srv = services.get(sid)
            service_totals[sid] = {
                "name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "revenue": 0.0, "count": 0,
            }
        service_totals[sid]["revenue"] += float(a.total_price or 0)
        service_totals[sid]["count"] += 1

    sorted_services = sorted(service_totals.values(), key=lambda x: x["revenue"], reverse=True)
    top_services = [
        TopService(
            service_id=list(service_totals.keys())[list(service_totals.values()).index(s)],
            service_name=s["name"],
            category=s["category"],
            total_revenue=round(s["revenue"], 2),
            total_count=s["count"],
            avg_price=round(s["revenue"] / s["count"], 2) if s["count"] else 0,
        )
        for s in sorted_services[:5]
    ]

    # --- 4. Прогноз на 3 месяца (скользящее среднее + тренд) ---
    forecast = []
    # Собираем общую выручку по месяцам (сумма по всем услугам)
    monthly_total: dict[str, float] = {}
    for a in appts:
        m = a.start_time.strftime("%Y-%m")
        monthly_total[m] = monthly_total.get(m, 0) + float(a.total_price or 0)

    if len(monthly_total) >= 3:
        sorted_months = sorted(monthly_total.keys())
        last_3 = sorted_months[-3:]

        # Средняя выручка за последние 3 месяца
        recent_revenues = [monthly_total[m] for m in last_3]
        avg_revenue = sum(recent_revenues) / len(recent_revenues)

        # Тренд: изменение между самым старым и самым новым месяцем из last_3
        if recent_revenues[0] > 0:
            trend = (recent_revenues[-1] - recent_revenues[0]) / recent_revenues[0]
        else:
            trend = 0.0

        # Уровень уверенности: чем больше данных, тем выше
        data_points = len(monthly_total)
        if data_points >= 6:
            confidence_width = 0.2  # ±20%
        elif data_points >= 4:
            confidence_width = 0.3  # ±30%
        else:
            confidence_width = 0.4  # ±40%

        # Прогноз на 3 месяца вперёд
        last_month_dt = datetime.strptime(sorted_months[-1] + "-01", "%Y-%m-%d")
        for i in range(1, 4):
            next_m = (last_month_dt + timedelta(days=32 * i)).strftime("%Y-%m")
            # Прогноз: среднее * (1 + тренд)^i (экспоненциальное сглаживание)
            projected = avg_revenue * ((1 + trend) ** i)
            forecast.append(ForecastPoint(
                month=next_m,
                forecast=round(projected, 2),
                lower_bound=round(projected * (1 - confidence_width), 2),
                upper_bound=round(projected * (1 + confidence_width), 2),
            ))

    return ServiceAnalyticsResponse(
        trends=trends,
        comparison=comparison,
        top_services=top_services,
        forecast=forecast,
    )

@router.get("/api/reports/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Отчёт по выручке: сводка, сравнение, детализация."""
    from datetime import datetime, date, time, timedelta

    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Период
    if start_date and end_date:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        e_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    else:
        if period == "day":
            s_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date + timedelta(days=1)
        elif period == "week":
            s_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date + timedelta(days=7)
        elif period == "month":
            s_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            e_date = (s_date + timedelta(days=32)).replace(day=1)
        else:  # year
            s_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date.replace(year=s_date.year + 1)

    # Предыдущий период
    prev_duration = (e_date - s_date).total_seconds()
    p_start = s_date - timedelta(seconds=prev_duration)
    p_end = s_date

    # Записи за текущий период
    appts_current = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.service),
            selectinload(Appointment.master),
            selectinload(Appointment.client),
            selectinload(Appointment.invoice),
        )
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= s_date,
            Appointment.start_time < e_date,
        )
        .order_by(Appointment.start_time)
    )
    current_appts = appts_current.scalars().all()

    # Записи за предыдущий период
    appts_previous = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= p_start,
            Appointment.start_time < p_end,
        )
    )
    prev_appts = appts_previous.scalars().all()

    current_revenue = sum(float(a.total_price or 0) for a in current_appts)
    prev_revenue = sum(float(a.total_price or 0) for a in prev_appts)
    current_count = len(current_appts)
    prev_count = len(prev_appts)

    change_percent = 0.0
    if prev_revenue > 0:
        change_percent = round((current_revenue - prev_revenue) / prev_revenue * 100, 1)

    # --- По услугам ---
    service_map: dict[int, dict] = {}
    for a in current_appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_map:
            srv = a.service
            service_map[sid] = {
                "name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "revenue": 0.0, "count": 0,
            }
        service_map[sid]["revenue"] += float(a.total_price or 0)
        service_map[sid]["count"] += 1

    by_service = [
        ServiceRevenueSummary(
            service_id=sid,
            service_name=d["name"],
            category=d["category"],
            total_revenue=round(d["revenue"], 2),
            total_count=d["count"],
            avg_price=round(d["revenue"] / d["count"], 2) if d["count"] else 0,
        )
        for sid, d in sorted(service_map.items(), key=lambda x: x[1]["revenue"], reverse=True)
    ]

    # --- По мастерам ---
    master_map: dict[int, dict] = {}
    for a in current_appts:
        mid = a.master_id or 0
        if mid not in master_map:
            name = "Без мастера"
            if a.master:
                name = a.master.full_name
            master_map[mid] = {"name": name, "revenue": 0.0, "count": 0}
        master_map[mid]["revenue"] += float(a.total_price or 0)
        master_map[mid]["count"] += 1

    by_master = [
        MasterRevenueSummary(
            master_id=mid, master_name=d["name"],
            total_revenue=round(d["revenue"], 2),
            completed_count=d["count"],
            avg_revenue=round(d["revenue"] / d["count"], 2) if d["count"] else 0,
        )
        for mid, d in sorted(master_map.items(), key=lambda x: x[1]["revenue"], reverse=True)
    ]

    # --- Детализация ---
    details = []
    from app.modules.appointments.close_service import snapshot_material_cost, snapshot_revenue
    for a in current_appts:
        material = snapshot_material_cost(a)
        price = snapshot_revenue(a)
        details.append(RevenueDetail(
            date=a.start_time.strftime("%Y-%m-%d %H:%M"),
            service_name=a.service.name if a.service else "—",
            master_name=a.master.full_name if a.master else "—",
            client_name=a.client.full_name if a.client else "—",
            total_price=price,
            material_cost=material,
            profit=price - material,
        ))

    total_profit = sum(d.profit for d in details)

    return RevenueReportResponse(
        total_revenue=round(current_revenue, 2),
        total_profit=round(total_profit, 2),
        period_comparison=[PeriodComparison(
            period=period,
            current_revenue=round(current_revenue, 2),
            previous_revenue=round(prev_revenue, 2),
            current_count=current_count,
            previous_count=prev_count,
            change_percent=change_percent,
        )],
        by_service=by_service,
        by_master=by_master,
        details=details,
    )

@router.get("/api/reports/revenue/csv")
async def export_revenue_csv(
    period: str = Query("month"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Экспорт отчёта по выручке в CSV."""
    from fastapi.responses import StreamingResponse
    import io

    # Получаем данные через тот же эндпоинт
    report = await get_revenue_report(
        period=period, start_date=start_date, end_date=end_date,
        current_user=current_user, db=db,
    )

    output = io.StringIO()
    output.write("sep=,\n")
    output.write("Дата,Услуга,Мастер,Клиент,Сумма,Материалы,Прибыль\n")

    for d in report.details:
        output.write(
            f"{d.date},{d.service_name},{d.master_name},{d.client_name},"
            f"{d.total_price},{d.material_cost},{d.profit}\n"
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=revenue_report_{period}.csv"},
    )

