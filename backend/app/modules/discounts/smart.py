"""Win-back и погодные акции: чистые матчеры + сводка для админки."""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, DiscountRule, Tenant, User, UserRole
from app.modules.ai.financier_service import (
    WeatherDay,
    city_from_tenant,
    fetch_weather_forecast,
)

WEATHER_KIND_LABELS = {
    "rain": "дождь",
    "freeze": "мороз",
    "heat": "жара",
    "dry": "сухо",
    "mild": "обычная",
}


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def days_since_visit(last_visit: datetime, now: datetime) -> int:
    last = as_utc(last_visit)
    current = as_utc(now)
    if last is None or current is None:
        return 0
    return (current - last).days


def win_back_applies(last_visit: datetime | None, now: datetime, min_absent_days: int) -> bool:
    """Клиент был, но не раньше чем min_absent_days назад."""
    if last_visit is None:
        return False
    try:
        days = int(min_absent_days)
    except (TypeError, ValueError):
        days = 60
    return days_since_visit(last_visit, now) >= days


def weather_kind_of_day(day: WeatherDay) -> str:
    if day.precip_mm >= 2:
        return "rain"
    if day.t_min <= 0 or day.t_max <= 2:
        return "freeze"
    if day.t_max >= 25:
        return "heat"
    if day.precip_mm < 1 and day.t_max >= 16:
        return "dry"
    return "mild"


def weather_rule_matches(conditions: dict | None, day: WeatherDay | None) -> bool:
    if not day or not isinstance(conditions, dict):
        return False
    kind = str(conditions.get("weather") or conditions.get("condition") or "").strip().lower()
    if kind == "rain":
        return day.precip_mm >= float(conditions.get("precip_mm_min", 2))
    if kind == "freeze":
        t_min_max = float(conditions.get("t_min_max", 0))
        t_max_max = float(conditions.get("t_max_max", 2))
        return day.t_min <= t_min_max or day.t_max <= t_max_max
    if kind == "heat":
        return day.t_max >= float(conditions.get("t_max_min", 25))
    if kind == "dry":
        precip_max = float(conditions.get("precip_mm_max", 1))
        t_max_min = float(conditions.get("t_max_min", 16))
        return day.precip_mm < precip_max and day.t_max >= t_max_min
    return False


def _local_date(when: datetime, tz_name: str) -> date:
    aware = as_utc(when) or datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return aware.astimezone(tz).date()


def pick_weather_day(days: list[WeatherDay], on_date: date) -> WeatherDay | None:
    iso = on_date.isoformat()
    for day in days:
        if day.date == iso:
            return day
    return None


async def weather_forecast_for_tenant(
    db: AsyncSession,
    tenant_id: UUID,
) -> tuple[list[WeatherDay], dict]:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
    geo = city_from_tenant(tenant)
    try:
        days = await fetch_weather_forecast(geo["lat"], geo["lon"], geo["tz"])
    except Exception:
        days = []
    return days, geo


async def weather_day_for(
    db: AsyncSession,
    tenant_id: UUID,
    when: datetime | None,
) -> WeatherDay | None:
    days, geo = await weather_forecast_for_tenant(db, tenant_id)
    on_date = _local_date(when or datetime.now(timezone.utc), geo.get("tz") or "UTC")
    return pick_weather_day(days, on_date)


async def list_win_back_candidates(
    db: AsyncSession,
    tenant_id: UUID,
    min_absent_days: int,
    now: datetime | None = None,
    limit: int = 20,
) -> list[dict]:
    current = as_utc(now) or datetime.now(timezone.utc)
    last_visits = (
        select(
            Appointment.client_id.label("client_id"),
            func.max(Appointment.start_time).label("last_visit"),
        )
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        )
        .group_by(Appointment.client_id)
        .subquery()
    )
    result = await db.execute(
        select(User, last_visits.c.last_visit)
        .join(last_visits, last_visits.c.client_id == User.id)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.client,
        )
    )
    rows: list[dict] = []
    for user, last_visit in result.all():
        if not win_back_applies(last_visit, current, min_absent_days):
            continue
        rows.append({
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "days_since": days_since_visit(last_visit, current),
            "last_visit": as_utc(last_visit).isoformat() if last_visit else None,
        })
    rows.sort(key=lambda r: r["days_since"], reverse=True)
    return rows[:limit]


async def smart_overview(db: AsyncSession, tenant_id: UUID) -> dict:
    now = datetime.now(timezone.utc)
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            (DiscountRule.valid_until == None) | (DiscountRule.valid_until >= now),
        )
    )
    rules = list(rules_result.scalars().all())

    days, geo = await weather_forecast_for_tenant(db, tenant_id)
    today = _local_date(now, geo.get("tz") or "UTC")
    today_weather = pick_weather_day(days, today)
    kind = weather_kind_of_day(today_weather) if today_weather else None

    weather_payload = {
        "city": geo.get("city") or "Москва",
        "date": today.isoformat(),
        "t_max": today_weather.t_max if today_weather else None,
        "t_min": today_weather.t_min if today_weather else None,
        "precip_mm": today_weather.precip_mm if today_weather else None,
        "kind": kind,
        "kind_label": WEATHER_KIND_LABELS.get(kind or "", None),
        "available": today_weather is not None,
    }

    weather_matches = []
    for rule in rules:
        if rule.type != "weather":
            continue
        cond = rule.conditions or {}
        weather_matches.append({
            "id": rule.id,
            "name": rule.name,
            "discount_percent": rule.discount_percent,
            "weather": (cond or {}).get("weather"),
            "will_apply": weather_rule_matches(cond, today_weather),
        })

    win_rules = [r for r in rules if r.type == "win_back"]
    min_days = None
    rule_name = None
    if win_rules:
        min_days = min(int((r.conditions or {}).get("max_recency_days", 60)) for r in win_rules)
        named = next(
            (r for r in win_rules if int((r.conditions or {}).get("max_recency_days", 60)) == min_days),
            win_rules[0],
        )
        rule_name = named.name

    clients = []
    if min_days is not None:
        clients = await list_win_back_candidates(db, tenant_id, min_days, now=now)

    return {
        "weather": weather_payload,
        "weather_matches": weather_matches,
        "win_back": {
            "min_absent_days": min_days,
            "rule_name": rule_name,
            "clients": clients,
        },
    }
