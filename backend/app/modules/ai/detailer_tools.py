"""Реализация функций ИИ-консультанта (Максим) из prompts/detailer.yaml.

Один экземпляр ``DetailerTools`` обслуживает один ход диалога: держит сессию БД,
клиента и помнит созданные за ход записи (чтобы send_master_brief нашёл мастера).
Все обработчики возвращают JSON-сериализуемые словари — их содержимое уходит
модели как tool-result.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.image_service import resolve_portfolio_url
from app.core.notification_service import create_notification
from app.models import (
    Appointment,
    Box,
    BoxService,
    Car,
    Material,
    Photo,
    Service,
    User,
)
from app.modules.ai.detailer_service import DEFAULT_DURATION, client_tz, day_slot_grid, load_catalog, suggest_slots
from app.modules.appointments.live_service import FLOOR_STATUSES

PAINT_TYPE_CODES = {
    "керамика": "ceramic",
    "керамик": "ceramic",
    "ceramic": "ceramic",
    "лак": "lacquer",
    "lacquer": "lacquer",
    "плёнка": "film",
    "пленка": "film",
    "film": "film",
    "не знаю": "unknown",
    "unknown": "unknown",
}
PAINT_TYPE_LABELS = {
    "ceramic": "Керамика",
    "lacquer": "Лак",
    "film": "Плёнка",
    "unknown": "Не знаю",
}
ACTIVE_APPOINTMENT_STATUSES = ("pending", "confirmed")


def _norm(value: str | None) -> str:
    return (value or "").lower().replace("ё", "е").strip()


def _split_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.replace(";", ",").replace("/", ",").replace("\n", ",")
    return [chunk.strip() for chunk in raw.split(",") if chunk.strip()]


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _overlaps(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < other_end and end > other_start


class DetailerTools:
    """Диспетчер функций промпта, привязанный к клиенту и его сессии БД."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, client: dict, tz_offset: int = 0):
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.tz_offset = tz_offset
        self._created: list[dict] = []

    # ------------------------------------------------------------------ utils
    @property
    def _client_id(self) -> int:
        return int(self.client["id"])

    async def _cars(self) -> list[Car]:
        result = await self.db.execute(
            select(Car)
            .where(Car.client_id == self._client_id, Car.tenant_id == self.tenant_id)
            .order_by(Car.created_at, Car.id)
        )
        return list(result.scalars().all())

    async def _client_car(self) -> Car | None:
        cars = await self._cars()
        return cars[0] if cars else None

    async def _match_service(self, name: str | None) -> Service | None:
        catalog = await load_catalog(self.db, self.tenant_id)
        if not catalog:
            return None
        target = _norm(name)
        if target:
            for service in catalog:
                if _norm(service.name) == target:
                    return service
            for service in catalog:
                sname = _norm(service.name)
                if sname and (target in sname or sname in target):
                    return service
            tokens = [t for t in target.split() if len(t) > 2]
            best, best_score = None, 0
            for service in catalog:
                blob = _norm(f"{service.name} {service.category or ''} {service.description or ''}")
                score = sum(1 for token in tokens if token in blob)
                if score > best_score:
                    best, best_score = service, score
            if best is not None:
                return best
        return catalog[0]

    async def _match_master(self, name: str | None) -> User | None:
        if not name:
            return None
        result = await self.db.execute(
            select(User).where(User.tenant_id == self.tenant_id, User.role == "master")
        )
        masters = list(result.scalars().all())
        target = _norm(name)
        for master in masters:
            if _norm(master.full_name) == target:
                return master
        for master in masters:
            mname = _norm(master.full_name)
            if target and (target in mname or any(part in mname for part in target.split() if len(part) > 2)):
                return master
        return None

    def _parse_slot_datetime(self, date_str: str | None, time_str: str | None) -> datetime | None:
        if not date_str or not time_str:
            return None
        tz = client_tz(self.tz_offset)
        text = time_str.strip()
        fmt = "%H:%M" if len(text) <= 5 else "%H:%M:%S"
        local = datetime.strptime(f"{date_str.strip()} {text}", f"%Y-%m-%d {fmt}")
        return local.replace(tzinfo=tz).astimezone(timezone.utc)

    # --------------------------------------------------------------- handlers
    async def get_client_profile(self) -> dict:
        cars = await self._cars()
        return {
            "client_name": self.client.get("full_name"),
            "has_profile": bool(cars),
            "cars": [
                {
                    "id": car.id,
                    "make": car.make,
                    "model": car.model,
                    "year": car.year,
                    "coating_type": PAINT_TYPE_LABELS.get(car.paint_type or "", "Не знаю"),
                    "glass_damage": ", ".join(car.glass_defects or []),
                    "special_requirements": ", ".join(car.care_requirements or []),
                    "general_info": car.condition_notes,
                }
                for car in cars
            ],
        }

    async def update_client_profile(
        self,
        car_model: str | None = None,
        coating_type: str | None = None,
        glass_damage: str | None = None,
        special_requirements: str | None = None,
        general_info: str | None = None,
    ) -> dict:
        car = await self._client_car()
        if car is None:
            if not car_model:
                return {"ok": False, "error": "Нет авто в профиле — уточни модель автомобиля."}
            make, _, model = car_model.strip().partition(" ")
            car = Car(
                client_id=self._client_id,
                tenant_id=self.tenant_id,
                make=make or "Авто",
                model=model.strip() or (make or "Авто"),
            )
            self.db.add(car)

        if car_model:
            make, _, model = car_model.strip().partition(" ")
            if make:
                car.make = make
            car.model = model.strip() or car.model or make

        if coating_type:
            car.paint_type = PAINT_TYPE_CODES.get(_norm(coating_type), "unknown")
        if glass_damage:
            car.glass_defects = _split_list(glass_damage)
        if special_requirements:
            car.care_requirements = _split_list(special_requirements)
        if general_info:
            car.condition_notes = general_info.strip()

        await self.db.commit()
        await self.db.refresh(car)
        return {
            "ok": True,
            "car_id": car.id,
            "car_model": f"{car.make} {car.model}".strip(),
            "coating_type": PAINT_TYPE_LABELS.get(car.paint_type or "", "Не знаю"),
            "glass_damage": car.glass_defects or [],
            "special_requirements": car.care_requirements or [],
            "general_info": car.condition_notes,
        }

    async def search_portfolio(
        self,
        service_name: str,
        query: str | None = None,
        limit: int = 4,
    ) -> dict:
        service = await self._match_service(service_name)
        hay = f"{service_name} {query or ''}"

        stmt = (
            select(Photo)
            .options(selectinload(Photo.uploader))
            .where(Photo.tenant_id == self.tenant_id, Photo.entity_type == "portfolio")
        )
        if service is not None:
            stmt = stmt.where(Photo.service_id == service.id)
        elif query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Photo.title.ilike(like), Photo.description.ilike(like)))

        stmt = stmt.order_by(Photo.is_primary.desc(), Photo.sort_order, Photo.id.desc())
        rows = list((await self.db.execute(stmt.limit(max(1, min(int(limit or 4), 12))))).scalars().all())

        # Если по услуге пусто — покажем любые работы, чтобы не оставить клиента без визуала
        if not rows and service is not None:
            fallback = await self.db.execute(
                select(Photo)
                .options(selectinload(Photo.uploader))
                .where(Photo.tenant_id == self.tenant_id, Photo.entity_type == "portfolio")
                .order_by(Photo.is_primary.desc(), Photo.sort_order, Photo.id.desc())
                .limit(max(1, min(int(limit or 4), 12)))
            )
            rows = list(fallback.scalars().all())

        photos = [
            {
                "image_url": resolve_portfolio_url(photo.url, hay),
                "master": photo.uploader.full_name if photo.uploader else None,
                "service": service.name if service else None,
                "title": photo.title,
                "description": photo.description,
            }
            for photo in rows
        ]
        return {"service": service.name if service else None, "count": len(photos), "photos": photos}

    async def search_products(self, query: str) -> dict:
        target = _norm(query)
        result = await self.db.execute(
            select(Material)
            .where(Material.tenant_id == self.tenant_id, Material.is_active == True)  # noqa: E712
            .order_by(Material.name)
        )
        products: list[dict] = []
        for material in result.scalars().all():
            blob = _norm(f"{material.name} {material.category or ''} {material.notes or ''}")
            if target and target not in blob:
                continue
            products.append(
                {
                    "name": material.name,
                    "category": material.category,
                    "unit": material.unit,
                    "purpose": material.notes,
                }
            )
            if len(products) >= 6:
                break
        return {
            "products": products,
            "note": "Цену на товары уточню у мастера.",
        }

    async def get_free_slots(
        self,
        service_names: list[str] | None = None,
        date: str | None = None,
        employee_name: str | None = None,
    ) -> dict:
        requested = [name for name in (service_names or []) if name]
        services = [await self._match_service(name) for name in requested] if requested else []
        services = [s for s in services if s is not None]
        duration = max((int(s.duration or DEFAULT_DURATION) for s in services), default=DEFAULT_DURATION)
        service_id = services[0].id if services else None

        if date:
            items = await day_slot_grid(
                self.db,
                self.tenant_id,
                date_str=date,
                duration_min=duration,
                service_id=service_id,
                tz_offset_minutes=self.tz_offset,
            )
            available = [slot for slot in items if slot.get("available")]
        else:
            available = await suggest_slots(
                self.db,
                self.tenant_id,
                duration_min=duration,
                service_id=service_id,
                tz_offset_minutes=self.tz_offset,
            )

        master = await self._match_master(employee_name) if employee_name else None
        if master is not None:
            busy = await self._busy_intervals(master.id, date)
            available = [
                slot
                for slot in available
                if slot.get("start_time")
                and slot.get("end_time")
                and not any(
                    _overlaps(
                        datetime.fromisoformat(slot["start_time"]),
                        datetime.fromisoformat(slot["end_time"]),
                        start,
                        end,
                    )
                    for start, end in busy
                )
            ]

        slots = [
            {
                "date": slot.get("date"),
                "time": slot.get("time"),
                "start_time": slot.get("start_time"),
                "employee_name": master.full_name if master else None,
                "box_name": slot.get("box_name"),
            }
            for slot in available[:6]
        ]
        return {
            "slots": slots,
            "duration_min": duration,
            "services": [s.name for s in services],
            "employee_name": master.full_name if master else employee_name,
        }

    async def create_appointment(self, bookings: list[dict] | None = None) -> dict:
        car = await self._client_car()
        if car is None:
            return {"ok": False, "error": "Нет авто в профиле — добавь автомобиль, и я запишу."}

        results: list[dict] = []
        for booking in bookings or []:
            service = await self._match_service(booking.get("service_name"))
            if service is None:
                results.append({"ok": False, "error": f"Услуга не найдена: {booking.get('service_name')}"})
                continue
            employee_name = booking.get("employee_name")
            master = await self._match_master(employee_name)
            if employee_name and master is None:
                results.append({"ok": False, "error": f"Мастер не найден: {employee_name}"})
                continue
            start = self._parse_slot_datetime(booking.get("date"), booking.get("time"))
            if start is None:
                results.append({"ok": False, "error": "Нужны дата и время записи."})
                continue

            end = start + timedelta(minutes=int(service.duration or DEFAULT_DURATION))
            box_id = await self._pick_box(service.id, start, end)
            appointment = Appointment(
                client_id=self._client_id,
                tenant_id=self.tenant_id,
                car_id=car.id,
                service_id=service.id,
                master_id=master.id if master else None,
                box_id=box_id,
                start_time=start,
                end_time=end,
                total_price=service.price,
                status="pending",
            )
            self.db.add(appointment)
            await self.db.commit()
            await self.db.refresh(appointment)

            record = {
                "ok": True,
                "appointment_id": appointment.id,
                "service_name": service.name,
                "employee_name": master.full_name if master else None,
                "start_time": start.isoformat(),
                "box_id": box_id,
            }
            self._created.append(record)
            results.append(record)

        return {
            "ok": bool(results) and all(item.get("ok") for item in results),
            "count": sum(1 for item in results if item.get("ok")),
            "bookings": results,
        }

    async def send_master_brief(
        self,
        employee_name: str | None = None,
        summary: str = "",
        features: str | None = None,
        images: list[str] | None = None,
    ) -> dict:
        appointment = await self._find_appointment(employee_name)
        if appointment is None:
            return {"ok": False, "error": "Нет записи для передачи мастеру."}

        parts = [summary.strip()] if summary and summary.strip() else []
        if features and features.strip():
            parts.append(f"Особенности: {features.strip()}")
        if images:
            parts.append("Фото: " + ", ".join(images))
        appointment.master_brief = "\n\n".join(parts)
        await self.db.commit()
        await self.db.refresh(appointment)

        if appointment.master_id:
            master = await self.db.get(User, appointment.master_id)
            await create_notification(
                self.db,
                appointment.master_id,
                self.tenant_id,
                title="Брифинг по записи",
                message=appointment.master_brief[:500],
                type="info",
                related_entity_type="appointment",
                related_entity_id=appointment.id,
            )
            master_name = master.full_name if master else employee_name
        else:
            master_name = employee_name

        return {"ok": True, "appointment_id": appointment.id, "employee_name": master_name}

    async def escalate_to_human(self, reason: str, client_message: str | None = None) -> dict:
        result = await self.db.execute(
            select(User).where(
                User.tenant_id == self.tenant_id,
                User.role.in_(("admin", "super_admin")),
            )
        )
        admins = list(result.scalars().all())
        message = f"Клиент {self.client.get('full_name')}: {reason}"
        if client_message:
            message += f"\nСообщение: {client_message}"
        for admin in admins:
            await create_notification(
                self.db,
                admin.id,
                self.tenant_id,
                title="Клиент просит администратора",
                message=message,
                type="warning",
                related_entity_type="client",
                related_entity_id=self._client_id,
            )
        return {"ok": bool(admins), "notified": len(admins)}

    # --------------------------------------------------------------- helpers
    async def _pick_box(self, service_id: int, start: datetime, end: datetime) -> int | None:
        result = await self.db.execute(
            select(Box)
            .where(Box.tenant_id == self.tenant_id, Box.is_active == True)  # noqa: E712
            .order_by(Box.sort_order, Box.id)
        )
        boxes = list(result.scalars().all())
        if not boxes:
            return None
        bs_result = await self.db.execute(
            select(BoxService.box_id).where(
                BoxService.tenant_id == self.tenant_id,
                BoxService.service_id == service_id,
            )
        )
        preferred = {row[0] for row in bs_result.all()}
        ordered = sorted(boxes, key=lambda b: (0 if b.id in preferred else 1, b.sort_order or 0, b.id))

        appts = await self.db.execute(
            select(Appointment).where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.status.in_(FLOOR_STATUSES),
                Appointment.start_time < end,
                Appointment.end_time > start,
            )
        )
        busy_appts = list(appts.scalars().all())
        for box in ordered:
            busy = False
            for appointment in busy_appts:
                if appointment.box_id != box.id:
                    continue
                a_start, a_end = _aware(appointment.start_time), _aware(appointment.end_time)
                if a_start and a_end and _overlaps(start, end, a_start, a_end):
                    busy = True
                    break
            if not busy:
                return box.id
        return ordered[0].id

    async def _busy_intervals(self, master_id: int, date_str: str | None) -> list[tuple[datetime, datetime]]:
        """Занятые интервалы мастера на дату (для фильтра слотов)."""
        if not date_str:
            return []
        tz = client_tz(self.tz_offset)
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(timezone.utc)
        day_end = day_start + timedelta(days=1)
        result = await self.db.execute(
            select(Appointment).where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.master_id == master_id,
                Appointment.status.in_(FLOOR_STATUSES),
                Appointment.start_time < day_end,
                Appointment.end_time > day_start,
            )
        )
        intervals: list[tuple[datetime, datetime]] = []
        for appointment in result.scalars().all():
            start, end = _aware(appointment.start_time), _aware(appointment.end_time)
            if start and end:
                intervals.append((start, end))
        return intervals

    async def _find_appointment(self, employee_name: str | None) -> Appointment | None:
        target = _norm(employee_name)
        for record in reversed(self._created):
            if not target or _norm(record.get("employee_name")) == target:
                found = await self.db.get(Appointment, record["appointment_id"])
                if found is not None:
                    return found

        stmt = (
            select(Appointment)
            .options(selectinload(Appointment.master))
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.client_id == self._client_id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
            .order_by(Appointment.start_time)
            .limit(1)
        )
        if employee_name:
            master = await self._match_master(employee_name)
            if master is not None:
                stmt = stmt.where(Appointment.master_id == master.id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


# Имя функции в промпте → метод DetailerTools
HANDLERS = {
    "get_client_profile": "get_client_profile",
    "update_client_profile": "update_client_profile",
    "search_portfolio": "search_portfolio",
    "search_products": "search_products",
    "get_free_slots": "get_free_slots",
    "create_appointment": "create_appointment",
    "send_master_brief": "send_master_brief",
    "escalate_to_human": "escalate_to_human",
}


async def dispatch(tools: DetailerTools, name: str, arguments: dict) -> dict:
    """Вызвать функцию промпта по имени. Неизвестная функция → ошибка модели."""
    method_name = HANDLERS.get(name)
    if method_name is None:
        return {"ok": False, "error": f"Функция '{name}' не поддерживается."}
    method = getattr(tools, method_name)
    return await method(**(arguments or {}))
