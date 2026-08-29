"""AI-финансист: сезон, погода, рекомендации причина → действие → эффект в ₽.

Чат POST /api/ai/financier не ломаем: здесь детерминированная сводка без LLM.
Погода — Open-Meteo; если сеть недоступна, остаётся календарный сезон.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, Box, Expense, Service, Tenant
from app.modules.appointments.close_service import snapshot_material_cost, snapshot_revenue

DEFAULT_CITY = {
    "city": "Москва",
    "lat": 55.7558,
    "lon": 37.6173,
    "tz": "Europe/Moscow",
}

SEASON_META = {
    "winter": {
        "label": "Зима",
        "months": "декабрь–февраль",
        "demand": "мойка и антиреагент; керамика и полировка почти не идут",
        "push": "wash",
    },
    "spring": {
        "label": "Весна",
        "months": "март–апрель",
        "demand": "мойка с деконтаминацией, битум, полировка",
        "push": "polish",
    },
    "summer": {
        "label": "Лето",
        "months": "май–август",
        "demand": "керамика и покрытия; мойка стабильна",
        "push": "ceramic",
    },
    "autumn": {
        "label": "Осень",
        "months": "сентябрь–ноябрь",
        "demand": "предзимняя защита, мойка в дожди",
        "push": "ceramic",
    },
}

NEEDLES = {
    "wash": ["мойк", "wash", "двухфаз"],
    "ceramic": ["керамик", "покрыт"],
    "polish": ["полир"],
    "interior": ["химчист", "салон", "кожа"],
}


@dataclass
class WeatherDay:
    date: str
    t_max: float
    t_min: float
    precip_mm: float


def season_id(dt: datetime) -> str:
    month = dt.month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4):
        return "spring"
    if month in (9, 10, 11):
        return "autumn"
    return "summer"


def season_context_line(dt: datetime | None = None) -> str:
    now = dt or datetime.now(timezone.utc)
    sid = season_id(now)
    meta = SEASON_META[sid]
    return f"Сезон: {meta['label']} ({meta['months']}). Спрос: {meta['demand']}."


def city_from_tenant(tenant: Tenant | None) -> dict:
    cfg = (tenant.config or {}) if tenant else {}
    return {
        "city": cfg.get("city") or DEFAULT_CITY["city"],
        "lat": float(cfg.get("lat") or DEFAULT_CITY["lat"]),
        "lon": float(cfg.get("lon") or DEFAULT_CITY["lon"]),
        "tz": cfg.get("tz") or DEFAULT_CITY["tz"],
    }


def _norm(value: str | None) -> str:
    return (value or "").lower().replace("ё", "е")


def pick_service(services: list[Service], kind: str) -> Service | None:
    needles = NEEDLES.get(kind) or []
    ranked: list[tuple[int, float, Service]] = []
    for svc in services:
        blob = _norm(f"{svc.name} {svc.category or ''} {svc.description or ''}")
        score = sum(1 for n in needles if n in blob)
        if score:
            ranked.append((score, float(svc.price or 0), svc))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ranked[0][2] if ranked else None


def _price(svc: Service | None, fallback: float = 2500) -> float:
    if svc is None:
        return fallback
    return float(svc.price or fallback)


async def fetch_weather_forecast(lat: float, lon: float, tz: str = "Europe/Moscow") -> list[WeatherDay]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&forecast_days=7&timezone={tz}"
    )
    async with httpx.AsyncClient(timeout=4.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    days: list[WeatherDay] = []
    for i, day in enumerate(dates):
        days.append(
            WeatherDay(
                date=str(day),
                t_max=float(tmax[i]) if i < len(tmax) and tmax[i] is not None else 0.0,
                t_min=float(tmin[i]) if i < len(tmin) and tmin[i] is not None else 0.0,
                precip_mm=float(precip[i]) if i < len(precip) and precip[i] is not None else 0.0,
            )
        )
    return days


def weather_outlook(days: list[WeatherDay], season: str) -> str:
    if not days:
        return SEASON_META[season]["demand"].capitalize() + "."
    near = days[:3]
    rain = sum(1 for d in near if d.precip_mm >= 2)
    snow = season == "winter" and any(d.t_max <= 1 and d.precip_mm >= 1 for d in near)
    freeze = any(d.t_min <= 0 for d in near)
    heat = any(d.t_max >= 28 for d in near)
    t_hi = max(d.t_max for d in near)
    t_lo = min(d.t_min for d in near)
    rain_mm = sum(d.precip_mm for d in near)
    bits = [f"3 дня: {t_lo:.0f}…{t_hi:.0f}°"]
    if rain:
        bits.append(f"дождь {rain} дн. ({rain_mm:.0f} мм)")
    if snow:
        bits.append("осадки с морозом")
    if freeze and not snow:
        bits.append("ночью заморозки")
    if heat:
        bits.append("жара")
    if rain == 0 and not freeze:
        bits.append("сухо — окно для покрытий" if season in ("spring", "summer", "autumn") else "без осадков")
    return ", ".join(bits) + "."


def _rec(
    rec_id: str,
    *,
    cause: str,
    action: str,
    effect_rub: float,
    horizon: str,
    kind: str,
) -> dict:
    return {
        "id": rec_id,
        "cause": cause,
        "action": action,
        "effect_rub": int(round(max(0, effect_rub))),
        "horizon": horizon,
        "kind": kind,
    }


def build_recommendations(
    *,
    season: str,
    days: list[WeatherDay],
    services: list[Service],
    occupancy: dict[str, int],
    box_revenue: dict[int, tuple[str, float]],
    net_profit: float,
    avg_check: float,
) -> list[dict]:
    wash = pick_service(services, "wash")
    ceramic = pick_service(services, "ceramic")
    polish = pick_service(services, "polish")
    interior = pick_service(services, "interior")
    wash_p = _price(wash, 2000)
    ceramic_p = _price(ceramic, 8000)
    polish_p = _price(polish, 5000)
    interior_p = _price(interior, 3500)
    check = avg_check or wash_p

    recs: list[dict] = []
    near = days[:3]
    rain_days = sum(1 for d in near if d.precip_mm >= 2)
    rain_mm = sum(d.precip_mm for d in near)
    freeze = any(d.t_min <= 0 for d in near) if near else False
    heat = any(d.t_max >= 28 for d in near) if near else False
    dry_warm = bool(near) and rain_days == 0 and any(d.t_max >= 16 for d in near) and not freeze

    if rain_days >= 2:
        extra = max(2, rain_days)
        recs.append(_rec(
            "weather-rain-wash",
            cause=f"За 3 дня дождь {rain_days} дн. ({rain_mm:.0f} мм) — машины будут грязными.",
            action=(
                f"Акция на {(wash.name if wash else 'мойку')} в окнах до/после дождя "
                "(слоты 9–12 и 18–20), не резать цену на керамику."
            ),
            effect_rub=wash_p * extra,
            horizon="3 дня",
            kind="weather",
        ))

    if freeze:
        recs.append(_rec(
            "weather-freeze",
            cause="Ночью 0° и ниже — покрытия на холодном ЛКП не держатся.",
            action="Снять керамику/полировку с ближайших слотов; греть бокс, продавать мойку и антиреагент.",
            effect_rub=wash_p * 2,
            horizon="3 дня",
            kind="weather",
        ))
    elif dry_warm and season in ("spring", "summer", "autumn"):
        target = ceramic or polish
        price = ceramic_p if ceramic else polish_p
        recs.append(_rec(
            "weather-dry-coat",
            cause="Сухо и тепло — окно для покрытий, без смыва в первые сутки.",
            action=(
                f"Пуш клиентам без визита 45+ дней: {(target.name if target else 'керамика/полировка')}. "
                "Ставить на утро, пока нет грозы."
            ),
            effect_rub=price * 2,
            horizon="7 дней",
            kind="weather",
        ))

    if heat:
        recs.append(_rec(
            "weather-heat-interior",
            cause="Жара: салон и кожа страдают, кузов лучше не полировать в пик дня.",
            action=(
                f"Предлагать {(interior.name if interior else 'химчистку салона')} "
                "и сдвигать полировку на утро/вечер."
            ),
            effect_rub=interior_p,
            horizon="3 дня",
            kind="weather",
        ))

    meta = SEASON_META[season]
    if season == "winter":
        recs.append(_rec(
            "season-winter",
            cause=f"{meta['label']}: реагенты и взвесь — повторные мойки, керамика почти не продаётся.",
            action=(
                f"Пакет «зима»: {(wash.name if wash else 'мойка')} + "
                f"{(interior.name if interior else 'химчистка ковриков/салона')}."
            ),
            effect_rub=(wash_p + interior_p * 0.5),
            horizon="месяц",
            kind="season",
        ))
    elif season == "spring":
        recs.append(_rec(
            "season-spring",
            cause="Весна: битум и зимняя плёнка на ЛКП, клиенты готовы к коррекции.",
            action=f"Допродажа деконтаминации к мойке и слоты на {(polish.name if polish else 'полировку')}.",
            effect_rub=polish_p,
            horizon="месяц",
            kind="season",
        ))
    elif season == "summer":
        recs.append(_rec(
            "season-summer",
            cause="Лето: пик спроса на защиту ЛКП, мойка не покрывает простой бокса.",
            action=f"Квота слотов на {(ceramic.name if ceramic else 'керамику')} 2–3 в день, не отдавать все боксы мойке.",
            effect_rub=ceramic_p,
            horizon="месяц",
            kind="season",
        ))
    else:
        recs.append(_rec(
            "season-autumn",
            cause="Осень: дожди и подготовка к реагентам — последний комфортный месяц для керамики.",
            action=f"Кампания «до зимы»: {(ceramic.name if ceramic else 'керамика')} клиентам с мойкой за лето.",
            effect_rub=ceramic_p,
            horizon="месяц",
            kind="season",
        ))

    counts = list(occupancy.values())
    peak = max(counts) if counts else 0
    if peak >= 3:
        weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        weak = [(wd, n) for wd, n in occupancy.items() if n <= peak * 0.4]
        if weak:
            wd, n = min(weak, key=lambda x: x[1])
            recs.append(_rec(
                "load-gap",
                cause=f"Просадка {weekdays[int(wd)]}: {n} записей против {peak} в пик.",
                action="Happy hours 15% на мойку 10:00–14:00 в слабый день, не на субботу.",
                effect_rub=check * 2,
                horizon="14 дней",
                kind="load",
            ))

    if len(box_revenue) >= 2:
        ranked = sorted(box_revenue.items(), key=lambda x: x[1][1])
        _weak_id, (weak_name, weak_rev) = ranked[0]
        _sid, (strong_name, strong_rev) = ranked[-1]
        if strong_rev >= 2 * max(weak_rev, 1) and strong_rev > 0:
            recs.append(_rec(
                "box-idle",
                cause=f"{weak_name} дал {weak_rev:.0f} ₽ при {strong_rev:.0f} ₽ у {strong_name}.",
                action=f"Перекинуть 2 слота защитных услуг в {weak_name} или акция только на этот бокс.",
                effect_rub=check * 2,
                horizon="месяц",
                kind="box",
            ))

    if net_profit < 0:
        recs.append(_rec(
            "pl-loss",
            cause=f"Месяц в минусе на {abs(net_profit):.0f} ₽ — постоянные расходы съедают чек.",
            action="Не резать химию вслепую: закрывать простой бокса и слабые дни, сверить аренду.",
            effect_rub=min(abs(net_profit) * 0.25, check * 6),
            horizon="месяц",
            kind="pnl",
        ))

    recs.sort(key=lambda r: r["effect_rub"], reverse=True)
    seen: set[str] = set()
    unique: list[dict] = []
    for item in recs:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique.append(item)
        if len(unique) >= 5:
            break
    return unique


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _weekday_load(appointments: list[Appointment], now: datetime) -> dict[str, int]:
    start = now - timedelta(days=14)
    counts: dict[str, int] = defaultdict(int)
    for appt in appointments:
        st = _aware(appt.start_time)
        if st is None or st < start or appt.status in ("cancelled", "no_show"):
            continue
        counts[str(st.weekday())] += 1
    return dict(counts)


async def build_financier_brief(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    now: datetime | None = None,
    weather_days: list[WeatherDay] | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    season = season_id(now)
    meta = SEASON_META[season]

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    geo = city_from_tenant(tenant)
    source = "season-only"
    days = weather_days
    if days is None:
        try:
            days = await fetch_weather_forecast(geo["lat"], geo["lon"], geo["tz"])
            source = "open-meteo"
        except Exception:
            days = []
            source = "season-only"

    services = list(
        (
            await db.execute(
                select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
            )
        ).scalars().all()
    )
    appts = list(
        (
            await db.execute(
                select(Appointment)
                .options(selectinload(Appointment.service), selectinload(Appointment.box))
                .where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.start_time >= month_start - timedelta(days=14),
                )
            )
        ).scalars().all()
    )
    month_appts = []
    for a in appts:
        st = _aware(a.start_time)
        if st and st >= month_start:
            month_appts.append(a)
    completed = [a for a in month_appts if a.status == "completed"]
    revenue = sum(snapshot_revenue(a) for a in completed)
    avg_check = (revenue / len(completed)) if completed else 0.0

    expenses = list(
        (
            await db.execute(
                select(Expense).where(
                    Expense.tenant_id == tenant_id,
                    Expense.expense_date >= month_start,
                )
            )
        ).scalars().all()
    )
    total_exp = sum(float(e.amount or 0) for e in expenses)
    materials = sum(snapshot_material_cost(a) for a in completed)
    net_profit = revenue - materials - total_exp

    boxes = list(
        (
            await db.execute(
                select(Box).where(Box.tenant_id == tenant_id, Box.is_active == True)
            )
        ).scalars().all()
    )
    box_revenue: dict[int, tuple[str, float]] = {b.id: (b.name, 0.0) for b in boxes}
    for a in completed:
        if a.box_id and a.box_id in box_revenue:
            name, val = box_revenue[a.box_id]
            box_revenue[a.box_id] = (name, val + snapshot_revenue(a))

    recs = build_recommendations(
        season=season,
        days=days or [],
        services=services,
        occupancy=_weekday_load(appts, now),
        box_revenue=box_revenue,
        net_profit=net_profit,
        avg_check=avg_check,
    )
    outlook = weather_outlook(days or [], season)
    return {
        "city": geo["city"],
        "source": source,
        "season": season,
        "season_label": meta["label"],
        "season_demand": meta["demand"],
        "outlook": outlook,
        "days": [
            {
                "date": d.date,
                "t_max": d.t_max,
                "t_min": d.t_min,
                "precip_mm": d.precip_mm,
            }
            for d in (days or [])[:7]
        ],
        "recommendations": recs,
        "month_revenue": round(revenue, 2),
        "net_profit": round(net_profit, 2),
        "avg_check": round(avg_check, 2),
    }
