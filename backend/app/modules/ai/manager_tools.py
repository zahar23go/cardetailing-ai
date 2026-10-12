"""Реализация функций ИИ-управляющего студией (prompts/manager.yaml).

Read-only операционные срезы для администратора салона: расписание на день,
загрузка боксов и мастеров, состав мастеров и записи, требующие внимания.
Каждый обработчик возвращает JSON-сериализуемый словарь — его содержимое уходит
модели как tool-result. Действия, меняющие данные (перенос записи, поручения),
осознанно вне минимальной версии.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Appointment, Box, MasterSkill, User, WorkingHours
from app.modules.ai.detailer_service import client_tz
from app.modules.analytics.spec import build_spec
from app.modules.appointments.live_service import FLOOR_STATUSES

# Период → окно загрузки в днях
_PERIOD_DAYS = {"day": 1, "week": 7, "month": 30}


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class ManagerTools:
    """Операционные функции управляющего, привязанные к тенанту и сессии БД."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, client: dict, tz_offset: int = 0):
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.tz_offset = tz_offset

    # ------------------------------------------------------------------ helpers
    def _day_window(self, date_str: str | None) -> tuple[datetime, datetime]:
        """UTC-окно [начало суток, +1 день) по локальной дате клиента."""
        tz = client_tz(self.tz_offset)
        if date_str:
            day = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            start = day.replace(tzinfo=tz)
        else:
            start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start.astimezone(timezone.utc)
        return start_utc, start_utc + timedelta(days=1)

    async def _active_boxes(self) -> list[Box]:
        result = await self.db.execute(
            select(Box)
            .where(Box.tenant_id == self.tenant_id, Box.is_active == True)  # noqa: E712
            .order_by(Box.sort_order, Box.id)
        )
        return list(result.scalars().all())

    # --------------------------------------------------------------- handlers
    async def get_day_schedule(self, date: str | None = None, **_kwargs) -> dict:
        """Расписание на дату (по умолчанию — на локальный «сегодня»)."""
        start, end = self._day_window(date)
        result = await self.db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.master),
                selectinload(Appointment.box),
                selectinload(Appointment.client),
                selectinload(Appointment.car),
            )
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.start_time >= start,
                Appointment.start_time < end,
                Appointment.status != "cancelled",
            )
            .order_by(Appointment.start_time)
        )
        appts = list(result.scalars().all())
        tz = client_tz(self.tz_offset)

        def row(a: Appointment) -> dict:
            return {
                "time": _utc(a.start_time).astimezone(tz).strftime("%H:%M"),
                "end_time": _utc(a.end_time).astimezone(tz).strftime("%H:%M"),
                "status": a.status,
                "service": a.service.name if a.service else None,
                "master": a.master.full_name if a.master else None,
                "box": a.box.name if a.box else None,
                "client": a.client.full_name if a.client else None,
                "car": f"{a.car.make} {a.car.model}".strip() if a.car else None,
            }

        by_status: dict[str, int] = {}
        for a in appts:
            by_status[a.status] = by_status.get(a.status, 0) + 1

        boxes = await self._active_boxes()
        return {
            "date": start.astimezone(tz).date().isoformat(),
            "total": len(appts),
            "by_status": by_status,
            "active_boxes": [b.name for b in boxes],
            "slots": [row(a) for a in appts],
        }

    async def get_workload(self, period: str = "week", **_kwargs) -> dict:
        """Загрузка боксов и мастеров за период (day / week / month)."""
        load_days = _PERIOD_DAYS.get((period or "week").lower(), 7)
        spec = await build_spec(self.db, self.tenant_id, load_days=load_days)

        def pack(rows) -> list[dict]:
            return [
                {
                    "name": r.name,
                    "occupancy_pct": r.occupancy_pct,
                    "busy_minutes": r.busy_minutes,
                    "capacity_minutes": r.capacity_minutes,
                    "appointments": r.appointments,
                }
                for r in rows
            ]

        boxes = pack(spec.boxes)
        busy = sum(b["busy_minutes"] for b in boxes)
        capacity = sum(b["capacity_minutes"] for b in boxes)
        salon = round(100.0 * busy / capacity, 1) if capacity else 0.0
        return {
            "period": period,
            "period_days": load_days,
            "salon_occupancy_pct": salon,
            "boxes": boxes,
            "masters": pack(spec.masters),
        }

    async def get_attention(self, **_kwargs) -> dict:
        """Записи, требующие внимания: ожидают, в работе, просрочены, не распределены."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.master),
                selectinload(Appointment.box),
                selectinload(Appointment.client),
            )
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.status.in_(FLOOR_STATUSES),
                Appointment.start_time < now + timedelta(days=1),
            )
            .order_by(Appointment.start_time)
        )
        appts = list(result.scalars().all())
        tz = client_tz(self.tz_offset)

        def row(a: Appointment) -> dict:
            return {
                "id": a.id,
                "datetime": _utc(a.start_time).astimezone(tz).strftime("%Y-%m-%d %H:%M"),
                "status": a.status,
                "service": a.service.name if a.service else None,
                "master": a.master.full_name if a.master else None,
                "box": a.box.name if a.box else None,
                "client": a.client.full_name if a.client else None,
            }

        return {
            "pending": [row(a) for a in appts if a.status == "pending"],
            "in_progress": [row(a) for a in appts if a.status == "in_progress"],
            "overdue": [
                row(a) for a in appts
                if a.status == "confirmed" and _utc(a.start_time) < now
            ],
            "unassigned": [row(a) for a in appts if a.master_id is None or a.box_id is None],
        }

    async def get_masters(self, **_kwargs) -> dict:
        """Состав мастеров: навыки и рабочие дни недели."""
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == self.tenant_id, User.role == "master")
            .order_by(User.full_name)
        )
        masters = list(result.scalars().all())

        skills_result = await self.db.execute(
            select(MasterSkill)
            .options(selectinload(MasterSkill.service))
            .where(MasterSkill.tenant_id == self.tenant_id)
        )
        by_master: dict[int, list[str]] = {}
        for skill in skills_result.scalars().all():
            if skill.service is not None:
                by_master.setdefault(skill.master_id, []).append(skill.service.name)

        hours_result = await self.db.execute(
            select(WorkingHours).where(WorkingHours.tenant_id == self.tenant_id)
        )
        days_by_master: dict[int, set[int]] = {}
        for hours in hours_result.scalars().all():
            if hours.is_working_day:
                days_by_master.setdefault(hours.master_id, set()).add(hours.day_of_week)

        return {
            "masters": [
                {
                    "name": m.full_name,
                    "skills": by_master.get(m.id, []) or ["универсал"],
                    "working_days": sorted(days_by_master.get(m.id, [])),
                }
                for m in masters
            ]
        }


# Имя функции в промпте → метод ManagerTools
HANDLERS = {
    "get_day_schedule": "get_day_schedule",
    "get_workload": "get_workload",
    "get_attention": "get_attention",
    "get_masters": "get_masters",
}


async def dispatch(tools: ManagerTools, name: str, arguments: dict) -> dict:
    """Вызвать функцию промпта по имени. Неизвестная функция → ошибка модели."""
    method_name = HANDLERS.get(name)
    if method_name is None:
        return {"ok": False, "error": f"Функция '{name}' не поддерживается."}
    method = getattr(tools, method_name)
    return await method(**(arguments or {}))
