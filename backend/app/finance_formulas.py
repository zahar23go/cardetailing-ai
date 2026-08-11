"""
Чистые формулы финансов / ИИ-Финансиста / скидок.

Все расчёты без БД и HTTP — удобно юнит-тестировать.
Источник истины для P&L, загрузки, маржи, break-even и рекомендаций.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Mapping, Sequence


def _round(value: float, digits: int) -> float:
    """Округление half-up (как в калькуляторе салона), не banker's round."""
    q = Decimal("1").scaleb(-digits)
    return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))


def _round2(value: float) -> float:
    return _round(value, 2)


def _round1(value: float) -> float:
    return _round(value, 1)


# ---------------------------------------------------------------------------
# Базовые KPI
# ---------------------------------------------------------------------------

def sum_revenue(transactions: Iterable[Mapping[str, Any]], *, completed_only: bool = True) -> float:
    """Выручка = сумма total_price (по умолчанию только status=completed)."""
    total = 0.0
    for t in transactions:
        if completed_only and t.get("status", "completed") != "completed":
            continue
        total += float(t.get("total_price") or 0)
    return _round2(total)


def avg_check(revenue: float, completed_count: int) -> float:
    """Средний чек = выручка / число завершённых записей."""
    if completed_count <= 0:
        return 0.0
    return _round2(revenue / completed_count)


def sum_material_cost(transactions: Iterable[Mapping[str, Any]], *, completed_only: bool = True) -> float:
    """Сумма материальных затрат по завершённым записям."""
    total = 0.0
    for t in transactions:
        if completed_only and t.get("status", "completed") != "completed":
            continue
        total += float(t.get("material_cost") or 0)
    return _round2(total)


def sum_expenses(expenses: Iterable[Mapping[str, Any]]) -> float:
    """Сумма постоянных / операционных расходов."""
    return _round2(sum(float(e.get("amount") or 0) for e in expenses))


def gross_profit(revenue: float, material_cost: float) -> float:
    """Валовая прибыль = выручка − материалы."""
    return _round2(revenue - material_cost)


def gross_margin_percent(revenue: float, material_cost: float) -> float:
    """Валовая маржа % = (валовая прибыль / выручка) × 100."""
    if revenue <= 0:
        return 0.0
    return _round1((revenue - material_cost) / revenue * 100)


def net_profit(revenue: float, material_cost: float, expenses: float) -> float:
    """Чистая прибыль = валовая − постоянные расходы."""
    return _round2(revenue - material_cost - expenses)


def net_margin_percent(revenue: float, material_cost: float, expenses: float) -> float:
    """Чистая маржа % = (чистая прибыль / выручка) × 100."""
    if revenue <= 0:
        return 0.0
    return _round1(net_profit(revenue, material_cost, expenses) / revenue * 100)


def service_margin_percent(price: float, cost: float) -> float:
    """Маржа услуги % = ((цена − себестоимость) / цена) × 100."""
    if price <= 0:
        return 0.0
    return _round1(((price - cost) / price) * 100)


def service_margin_raw(price: float, cost: float) -> float:
    """Маржа услуги 0…1 = (цена − себестоимость) / цена, clamp."""
    if price <= 0:
        return 0.0
    raw = (price - cost) / price
    return max(0.0, min(1.0, raw))


def resolve_service_cost(cost_price: float | None, material_cost: float | None) -> float:
    """Себестоимость: cost_price если > 0, иначе material_cost."""
    cp = float(cost_price or 0)
    if cp > 0:
        return cp
    return float(material_cost or 0)


# ---------------------------------------------------------------------------
# P&L агрегация
# ---------------------------------------------------------------------------

def compute_pl(
    transactions: Sequence[Mapping[str, Any]],
    expenses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Полный P&L за период по транзакциям и расходам."""
    completed = [t for t in transactions if t.get("status", "completed") == "completed"]
    revenue = sum_revenue(completed, completed_only=False)
    materials = sum_material_cost(completed, completed_only=False)
    fixed = sum_expenses(expenses)
    count = len(completed)

    by_service: dict[Any, dict[str, Any]] = {}
    for t in completed:
        sid = t.get("service_id")
        if sid is None:
            continue
        if sid not in by_service:
            by_service[sid] = {
                "service_id": sid,
                "service_name": t.get("service_name") or f"Услуга #{sid}",
                "total_revenue": 0.0,
                "total_material_cost": 0.0,
                "appointment_count": 0,
            }
        by_service[sid]["total_revenue"] += float(t.get("total_price") or 0)
        by_service[sid]["total_material_cost"] += float(t.get("material_cost") or 0)
        by_service[sid]["appointment_count"] += 1

    service_margins = []
    for s in by_service.values():
        gp = s["total_revenue"] - s["total_material_cost"]
        mp = _round1(gp / s["total_revenue"] * 100) if s["total_revenue"] else 0.0
        service_margins.append({
            **s,
            "total_revenue": _round2(s["total_revenue"]),
            "total_material_cost": _round2(s["total_material_cost"]),
            "gross_profit": _round2(gp),
            "margin_percent": mp,
        })
    service_margins.sort(key=lambda x: x["appointment_count"], reverse=True)

    expenses_by_category: dict[str, float] = {}
    for e in expenses:
        cat = e.get("category") or "other"
        expenses_by_category[cat] = expenses_by_category.get(cat, 0.0) + float(e.get("amount") or 0)

    return {
        "total_revenue": revenue,
        "completed_appointments": count,
        "avg_check": avg_check(revenue, count),
        "total_material_cost": materials,
        "total_expenses": fixed,
        "expenses_by_category": {k: _round2(v) for k, v in expenses_by_category.items()},
        "gross_profit": gross_profit(revenue, materials),
        "gross_margin_percent": gross_margin_percent(revenue, materials),
        "net_profit": net_profit(revenue, materials, fixed),
        "net_margin_percent": net_margin_percent(revenue, materials, fixed),
        "service_margins": service_margins,
    }


# ---------------------------------------------------------------------------
# Break-even / прогноз
# ---------------------------------------------------------------------------

def contribution_ratio(revenue: float, material_cost: float, *, default: float = 0.4) -> float:
    """Доля вклада после материалов. Если выручки нет — default 0.4."""
    if revenue <= 0:
        return default
    return (revenue - material_cost) / revenue


def break_even_revenue(fixed_costs: float, contrib_ratio: float) -> float:
    """Точка безубыточности = постоянные / contribution ratio."""
    if contrib_ratio <= 0:
        return 0.0
    return _round2(fixed_costs / contrib_ratio)


def forecast_profit(revenue: float, material_cost: float, fixed_costs: float) -> float:
    """Прогноз прибыли = выручка − материалы − постоянные."""
    return _round2(revenue - material_cost - fixed_costs)


# ---------------------------------------------------------------------------
# Загрузка / Happy Hours
# ---------------------------------------------------------------------------

def avg_load(count: float, weekday_occurrences: int) -> float:
    """Средняя загрузка слота = число записей / число таких дней в периоде."""
    return count / max(weekday_occurrences, 1)


def heatmap_intensity(count: float, max_count: float) -> float:
    """Интенсивность ячейки теплокарты 0…1."""
    if max_count <= 0:
        return 0.0
    return count / max_count


def discount_percent_relative(hour_load: float, peak_load: float) -> int:
    """
    % Happy Hours относительно пика группы (Пн–Пт / Сб / Вс).

    ratio = hour_load / peak_load
    ≥0.55 → 0%, ≥0.35 → 10%, ≥0.20 → 15%, <0.12 или 0 → 25%, иначе 20%.
    """
    if peak_load <= 0:
        return 25
    ratio = hour_load / peak_load
    if ratio >= 0.55:
        return 0
    if ratio >= 0.35:
        return 10
    if ratio >= 0.20:
        return 15
    if hour_load <= 0 or ratio < 0.12:
        return 25
    return 20


def discount_roi(
    times_used: int,
    discount_cost: float,
    avg_check_value: float,
    *,
    lift_factor: float = 0.6,
) -> dict[str, Any]:
    """
    Эвристика ROI скидки:
      extra_revenue ≈ times_used × avg_check × 0.6
      roi% = ((extra − cost) / cost) × 100
      verdict: ≥20 держать, ≥0 пересмотреть, иначе отключить
    """
    extra = _round2(times_used * avg_check_value * lift_factor) if avg_check_value else 0.0
    if discount_cost > 0:
        roi_pct = _round1(((extra - discount_cost) / discount_cost) * 100)
    else:
        roi_pct = 100.0 if times_used > 0 else 0.0
    if roi_pct >= 20:
        verdict = "держать"
    elif roi_pct >= 0:
        verdict = "пересмотреть"
    else:
        verdict = "отключить"
    return {
        "estimated_extra_revenue": extra,
        "roi_percent": roi_pct,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Рекомендации скидок по услугам
# ---------------------------------------------------------------------------

def percent_from_priority(priority: float) -> int:
    """≥0.7 → 20–30%, 0.45–0.69 → 10–20%, иначе 0."""
    if priority >= 0.7:
        t = min(1.0, (priority - 0.7) / 0.3)
        return int(round(20 + t * 10))
    if priority >= 0.45:
        t = (priority - 0.45) / 0.25
        return int(round(10 + t * 10))
    return 0


def service_discount_priority(popularity: float, margin_raw: float) -> float:
    """
    priority = volume_need×0.55 + margin_need×0.45
    volume_need = 1 − popularity, margin_need = 1 − margin_raw
    """
    volume_need = 1.0 - popularity
    margin_need = 1.0 - margin_raw
    return volume_need * 0.55 + margin_need * 0.45


def overhead_pressure(fixed_month: float, revenue_month: float) -> float:
    """Давление постоянных = fixed / max(revenue, 1)."""
    return fixed_month / max(revenue_month, 1.0)


def apply_overhead_boost(suggested: int, pressure: float) -> int:
    """На низкомаржинальных: pressure ≥0.20 → +5, ≥0.35 → +8, cap 30%."""
    if pressure >= 0.35:
        return min(30, suggested + 8)
    if pressure >= 0.20:
        return min(30, suggested + 5)
    return suggested


HIGH_MARGIN_PROTECT = 0.70
MIN_PRIORITY = 0.40


def should_protect_high_margin(margin_raw: float, is_low_volume: bool) -> bool:
    """Высокомаржинальные с нормальным спросом не режем."""
    return margin_raw >= HIGH_MARGIN_PROTECT and not is_low_volume


def is_low_volume(bookings: int, max_bookings: int, popularity: float) -> bool:
    return bookings <= max(1, int(max_bookings * 0.45)) or popularity <= 0.45


def is_low_margin(margin_raw: float, margin_median: float) -> bool:
    return margin_raw <= margin_median or margin_raw < 0.55


# ---------------------------------------------------------------------------
# Инсайты по расходам (rule-based «ИИ»)
# ---------------------------------------------------------------------------

def category_share_percent(amount: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return _round1(amount / total * 100)


def expense_mom_growth(prev: float, cur: float) -> float | None:
    """Рост категории MoM в %. None если prev=0."""
    if prev <= 0:
        return None
    return (cur - prev) / prev * 100


def rent_share_warn(rent_month: float, revenue_month: float, *, threshold: float = 25.0) -> bool:
    """Аренда ≥ 25% выручки — предупреждение."""
    if revenue_month <= 0 or rent_month <= 0:
        return False
    return (rent_month / revenue_month * 100) >= threshold


def marketing_roi_proxy(revenue_month: float, marketing_month: float) -> float | None:
    """Выручка / реклама. None если рекламы нет."""
    if marketing_month <= 0:
        return None
    return revenue_month / marketing_month


def build_expense_insights(
    *,
    revenue_month: float,
    material_month: float,
    fixed_month: float,
    rent_month: float = 0.0,
    marketing_month: float = 0.0,
    prev_by_category: Mapping[str, float] | None = None,
    cur_by_category: Mapping[str, float] | None = None,
    category_labels: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Rule-based инсайты (как в /api/analytics/expenses)."""
    insights: list[dict[str, Any]] = []
    labels = category_labels or {}

    if prev_by_category and cur_by_category:
        for cat, prev_v in prev_by_category.items():
            cur_v = cur_by_category.get(cat, 0.0)
            if prev_v > 0 and cur_v > prev_v * 1.3:
                growth = expense_mom_growth(prev_v, cur_v) or 0.0
                insights.append({
                    "type": "anomaly",
                    "severity": "critical" if growth >= 40 else "warn",
                    "title": f"Рост: {labels.get(cat, cat)}",
                    "growth_percent": _round1(growth),
                })

    if rent_share_warn(rent_month, revenue_month):
        share = rent_month / revenue_month * 100
        insights.append({
            "type": "tip",
            "severity": "warn",
            "title": "Аренда дорогая относительно выручки",
            "share_percent": _round1(share),
        })

    roi = marketing_roi_proxy(revenue_month, marketing_month)
    if roi is not None:
        if roi < 5:
            insights.append({
                "type": "tip",
                "severity": "warn",
                "title": "Реклама может быть неэффективна",
                "roi_proxy": _round1(roi),
            })
        elif roi >= 10:
            insights.append({
                "type": "tip",
                "severity": "info",
                "title": "Реклама работает",
                "roi_proxy": _round1(roi),
            })

    ratio = contribution_ratio(revenue_month, material_month)
    be = break_even_revenue(fixed_month, ratio)
    fp = forecast_profit(revenue_month, material_month, fixed_month)
    insights.append({
        "type": "break_even",
        "severity": "info",
        "title": "Точка безубыточности",
        "break_even_revenue": be,
    })
    insights.append({
        "type": "forecast",
        "severity": "info" if fp >= 0 else "warn",
        "title": "Прогноз прибыли (месяц)",
        "forecast_profit": fp,
    })
    return insights


# ---------------------------------------------------------------------------
# Контекст ИИ-Финансиста (агрегация без LLM)
# ---------------------------------------------------------------------------

def build_financier_context_metrics(
    transactions: Sequence[Mapping[str, Any]],
    *,
    total_clients: int = 0,
    total_masters: int = 0,
) -> dict[str, Any]:
    """Метрики, которые уходят в промпт ИИ-Финансиста."""
    completed = [t for t in transactions if t.get("status") == "completed"]
    pending = [t for t in transactions if t.get("status") == "pending"]
    revenue = sum_revenue(completed, completed_only=False)

    masters: dict[Any, dict[str, Any]] = {}
    for t in completed:
        mid = t.get("master_id")
        if not mid:
            continue
        if mid not in masters:
            masters[mid] = {
                "name": t.get("master_name") or f"мастер #{mid}",
                "completed": 0,
                "revenue": 0.0,
            }
        masters[mid]["completed"] += 1
        masters[mid]["revenue"] += float(t.get("total_price") or 0)

    services: dict[Any, dict[str, Any]] = {}
    for t in transactions:
        sid = t.get("service_id")
        if not sid:
            continue
        if sid not in services:
            services[sid] = {
                "name": t.get("service_name") or f"услуга #{sid}",
                "count": 0,
            }
        services[sid]["count"] += 1

    return {
        "total_clients": total_clients,
        "total_masters": total_masters,
        "total_appointments": len(transactions),
        "completed_appointments": len(completed),
        "pending_appointments": len(pending),
        "month_revenue": revenue,
        "avg_check": avg_check(revenue, len(completed)),
        "masters": sorted(masters.values(), key=lambda x: x["completed"], reverse=True),
        "services": sorted(services.values(), key=lambda x: x["count"], reverse=True),
    }
