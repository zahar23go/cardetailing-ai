"""Функции финансового ассистента (prompts/financier.yaml) — реальные данные из БД.

Возвращают JSON-сериализуемые словари (tool-result для LLM). Расчёты переиспользуют
проверенные формулы проекта:
  • ``snapshot_revenue`` (appointments.close_service) — выручка (чек закрытия или цена записи);
  • ``build_spec`` (analytics.spec) — загрузка боксов/мастеров и когорты;
  • ``avg_check`` (finance_formulas) — средний чек.
Все выборки ограничены ``tenant_id`` вызывающего.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.finance_formulas import avg_check as _avg_check
from app.models import Appointment
from app.modules.analytics.spec import build_spec
from app.modules.appointments.close_service import snapshot_revenue

# Период удержания → глубина окна в месяцах
_MONTHS_BY_PERIOD = {"month": 3, "quarter": 6, "year": 12}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip()).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _period_start(period: str | None, now: datetime) -> datetime:
    p = (period or "month").lower()
    if p == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if p == "week":
        return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if p == "quarter":
        return (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=92)).replace(day=1)
    if p == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)  # month


def _period_days(period: str | None, now: datetime) -> int:
    p = (period or "month").lower()
    if p == "day":
        return 1
    if p == "week":
        return 7
    if p == "quarter":
        return 92
    if p == "year":
        return 365
    return max(1, now.day)


def _horizon_days(horizon: str | None) -> int:
    raw = (horizon or "30d").strip().lower()
    if raw in ("day", "today"):
        return 1
    if raw in ("week", "7d", "7"):
        return 7
    if raw in ("month", "30d", "30"):
        return 30
    if raw in ("quarter", "90d", "90"):
        return 90
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 30


class FinancierTools:
    """Диспетчер функций финансиста: реальные агрегаты по БД (tenant-scoped)."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, client: dict, tz_offset: int = 0):
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.tz_offset = tz_offset

    # ------------------------------------------------------------------ data
    async def _completed(self, start: datetime, end: datetime | None = None) -> list[Appointment]:
        """Завершённые визиты за период со связями (selectinload — без lazy-load в async)."""
        end = end or _now()
        result = await self.db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.master),
                selectinload(Appointment.invoice),
            )
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.status == "completed",
                Appointment.start_time >= start,
                Appointment.start_time < end + timedelta(days=1),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _revenue(appointment: Appointment) -> float:
        return snapshot_revenue(appointment)

    async def _occupancy(self, load_days: int) -> tuple[float, list[dict], dict]:
        """Загрузка боксов/мастеров за ``load_days`` дней (переиспользует analytics.build_spec)."""
        spec = await build_spec(self.db, self.tenant_id, load_days=load_days)
        busy = sum(b.busy_minutes for b in spec.boxes)
        capacity = sum(b.capacity_minutes for b in spec.boxes)
        salon = round(100.0 * busy / capacity, 1) if capacity else 0.0
        masters = [
            {
                "name": m.name,
                "occupancy": m.occupancy_pct,
                "busy_minutes": m.busy_minutes,
                "capacity_minutes": m.capacity_minutes,
                "appointments": m.appointments,
            }
            for m in spec.masters
        ]
        return salon, masters, {"boxes": len(spec.boxes), "busy_minutes": busy, "capacity_minutes": capacity}

    async def _retention(self, start: datetime, end: datetime) -> dict:
        """Доля клиентов с повторными визитами (по разным месяцам) за окно."""
        result = await self.db.execute(
            select(Appointment.client_id, Appointment.start_time).where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.status == "completed",
                Appointment.start_time >= start,
                Appointment.start_time < end,
            )
        )
        months_by_client: dict[int, set[str]] = defaultdict(set)
        for client_id, start_time in result.all():
            dt = _aware(start_time)
            if dt is not None:
                months_by_client[client_id].add(dt.strftime("%Y-%m"))
        total = len(months_by_client)
        repeat = sum(1 for months in months_by_client.values() if len(months) >= 2)
        return {
            "rate": round(100.0 * repeat / total, 1) if total else 0.0,
            "returning_clients": repeat,
            "total_clients": total,
        }

    # --------------------------------------------------------------- handlers
    async def get_kpi(self, period: str = "month", **_kwargs) -> dict:
        now = _now()
        start = _period_start(period, now)
        completed = await self._completed(start, now)
        revenue = round(sum(self._revenue(a) for a in completed), 2)
        salon, _masters, _load = await self._occupancy(_period_days(period, now))
        months = _MONTHS_BY_PERIOD.get((period or "month").lower(), 3)
        retention = await self._retention(now - timedelta(days=months * 31), now)
        return {
            "period": period,
            "revenue": revenue,
            "occupancy": salon,
            "retention": retention["rate"],
            "avg_check": _avg_check(revenue, len(completed)),
            "completed_appointments": len(completed),
        }

    async def get_revenue_breakdown(
        self,
        period: str = "month",
        date_from: str | None = None,
        date_to: str | None = None,
        **_kwargs,
    ) -> dict:
        now = _now()
        start = _parse_date(date_from) or _period_start(period, now)
        end = _parse_date(date_to) or now
        completed = await self._completed(start, end)

        services: dict[str, dict] = {}
        masters: dict[str, dict] = {}
        days: dict[str, dict] = {}
        for a in completed:
            rev = self._revenue(a)
            sname = a.service.name if a.service else f"Услуга #{a.service_id}"
            svc = services.setdefault(str(a.service_id), {"name": sname, "revenue": 0.0, "count": 0})
            svc["revenue"] += rev
            svc["count"] += 1

            mname = a.master.full_name if a.master else "Без мастера"
            mst = masters.setdefault(str(a.master_id or 0), {"name": mname, "revenue": 0.0, "count": 0})
            mst["revenue"] += rev
            mst["count"] += 1

            dt = _aware(a.start_time)
            dkey = dt.date().isoformat() if dt else ""
            day = days.setdefault(dkey, {"date": dkey, "revenue": 0.0, "count": 0})
            day["revenue"] += rev
            day["count"] += 1

        def _pack(bucket: dict[str, dict]) -> list[dict]:
            rows = sorted(bucket.values(), key=lambda r: r["revenue"], reverse=True)
            for row in rows:
                row["revenue"] = round(row["revenue"], 2)
            return rows

        total = round(sum(row["revenue"] for row in services.values()), 2)
        return {
            "period": period,
            "total_revenue": total,
            "services": _pack(services),
            "masters": _pack(masters),
            "days": sorted(_pack(days), key=lambda r: r["date"]),
        }

    async def get_occupancy(self, period: str = "month", **_kwargs) -> dict:
        now = _now()
        load_days = _period_days(period, now)
        salon, masters, load = await self._occupancy(load_days)
        return {
            "period": period,
            "period_days": load_days,
            "salon": salon,
            "masters": masters,
            "load": load,
        }

    async def get_customer_retention(self, period: str = "month", **_kwargs) -> dict:
        now = _now()
        months = _MONTHS_BY_PERIOD.get((period or "month").lower(), 6)
        window_start = (now.replace(day=1) - timedelta(days=months * 31)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        spec = await build_spec(self.db, self.tenant_id, cohort_months=months)
        cohorts = [
            {
                "cohort": c.cohort,
                "size": c.size,
                "cells": [
                    {"offset": cell.offset, "clients": cell.clients, "rate": cell.rate}
                    for cell in c.cells
                ],
            }
            for c in spec.cohorts
        ]
        summary = await self._retention(window_start, now)
        return {
            "period": period,
            "cohorts": cohorts,
            "repeat_rate": summary["rate"],
            "returning_clients": summary["returning_clients"],
            "total_clients": summary["total_clients"],
        }

    async def forecast(self, horizon: str = "30d", **_kwargs) -> dict:
        now = _now()
        days = _horizon_days(horizon)
        lookback_days = 30
        completed = await self._completed(now - timedelta(days=lookback_days), now)
        total = sum(self._revenue(a) for a in completed)
        daily = total / lookback_days
        salon, _masters, _load = await self._occupancy(lookback_days)
        return {
            "horizon": horizon,
            "horizon_days": days,
            "revenue": round(daily * days, 2),
            "occupancy": salon,
            "basis": {
                "lookback_days": lookback_days,
                "daily_revenue": round(daily, 2),
                "completed_appointments": len(completed),
            },
        }


# Имя функции в промпте → метод FinancierTools
HANDLERS = {
    "get_kpi": "get_kpi",
    "get_revenue_breakdown": "get_revenue_breakdown",
    "get_occupancy": "get_occupancy",
    "get_customer_retention": "get_customer_retention",
    "forecast": "forecast",
}


async def dispatch(tools: FinancierTools, name: str, arguments: dict) -> dict:
    """Вызвать функцию финансиста по имени. Неизвестная функция → ошибка модели."""
    method_name = HANDLERS.get(name)
    if method_name is None:
        return {"ok": False, "error": f"Функция '{name}' не поддерживается."}
    method = getattr(tools, method_name)
    return await method(**(arguments or {}))
