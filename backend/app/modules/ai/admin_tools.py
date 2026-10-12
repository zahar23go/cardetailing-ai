"""Реализация функций ИИ-администратора (prompts/admin.yaml).

Конфигурация салона: услуги и цены, боксы, скидки/акции, мастера. Чтение —
списки текущих настроек; запись — только точечные операции (создать/обновить,
включить/выключить). Жёстких удалений нет: услуги и боксы выключаются (``is_active``).

Каждый обработчик возвращает JSON-сериализуемый словарь — его содержимое уходит
модели как tool-result. Порядок «сначала подтверди, потом меняй» задаётся промптом.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.models import Box, DiscountRule, Service, User

DISCOUNT_TYPES = ("happy_hours", "frequency", "win_back", "weather", "cashback", "service", "client")


def _norm(value: str | None) -> str:
    return (value or "").lower().replace("ё", "е").strip()


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%H:%M").time()


def _parse_valid_until(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.strip()).replace(tzinfo=timezone.utc)


class AdminTools:
    """Настройки салона, привязанные к тенанту и сессии БД."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, client: dict, tz_offset: int = 0):
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.tz_offset = tz_offset

    # ------------------------------------------------------------------ helpers
    async def _find_service(self, name: str | None) -> Service | None:
        if not name:
            return None
        result = await self.db.execute(
            select(Service).where(Service.tenant_id == self.tenant_id)
        )
        target = _norm(name)
        for service in result.scalars().all():
            if _norm(service.name) == target:
                return service
        return None

    async def _find_box(self, name: str | None) -> Box | None:
        if not name:
            return None
        result = await self.db.execute(
            select(Box).where(Box.tenant_id == self.tenant_id)
        )
        target = _norm(name)
        for box in result.scalars().all():
            if _norm(box.name) == target:
                return box
        return None

    async def _find_discount(self, name: str | None) -> DiscountRule | None:
        if not name:
            return None
        result = await self.db.execute(
            select(DiscountRule).where(DiscountRule.tenant_id == self.tenant_id)
        )
        target = _norm(name)
        for rule in result.scalars().all():
            if _norm(rule.name) == target:
                return rule
        return None

    # ------------------------------------------------------------------ read
    async def list_services(self, **_kwargs) -> dict:
        """Список услуг с ценами и себестоимостью."""
        result = await self.db.execute(
            select(Service).where(Service.tenant_id == self.tenant_id).order_by(Service.name)
        )
        return {
            "services": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "price": float(s.price or 0),
                    "duration": int(s.duration or 0),
                    "material_cost": float(s.material_cost or 0),
                    "cost_price": float(s.cost_price or 0),
                    "is_active": bool(s.is_active),
                }
                for s in result.scalars().all()
            ]
        }

    async def list_boxes(self, **_kwargs) -> dict:
        """Список боксов/зон."""
        result = await self.db.execute(
            select(Box)
            .where(Box.tenant_id == self.tenant_id)
            .order_by(Box.sort_order, Box.id)
        )
        return {
            "boxes": [
                {
                    "id": b.id,
                    "name": b.name,
                    "color": b.color,
                    "sort_order": b.sort_order,
                    "is_active": bool(b.is_active),
                }
                for b in result.scalars().all()
            ]
        }

    async def list_discounts(self, **_kwargs) -> dict:
        """Список правил скидок."""
        result = await self.db.execute(
            select(DiscountRule)
            .where(DiscountRule.tenant_id == self.tenant_id)
            .order_by(DiscountRule.name)
        )
        return {
            "discounts": [
                {
                    "id": d.id,
                    "name": d.name,
                    "type": d.type,
                    "discount_percent": d.discount_percent,
                    "slot_start": d.slot_start.strftime("%H:%M") if d.slot_start else None,
                    "slot_end": d.slot_end.strftime("%H:%M") if d.slot_end else None,
                    "service_id": d.service_id,
                    "is_active": bool(d.is_active),
                }
                for d in result.scalars().all()
            ]
        }

    async def list_staff(self, **_kwargs) -> dict:
        """Сотрудники салона: мастера и администраторы."""
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == self.tenant_id, User.role.in_(("master", "admin", "super_admin")))
            .order_by(User.role, User.full_name)
        )
        return {
            "staff": [
                {
                    "id": u.id,
                    "name": u.full_name,
                    "phone": u.phone,
                    "role": u.role,
                    "commission_percent": u.commission_percent,
                }
                for u in result.scalars().all()
            ]
        }

    # ------------------------------------------------------------------ write
    async def upsert_service(
        self,
        name: str,
        price: float | None = None,
        duration: int | None = None,
        category: str | None = None,
        material_cost: float | None = None,
        cost_price: float | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        **_kwargs,
    ) -> dict:
        """Создать услугу по имени или обновить существующую (переданные поля)."""
        service = await self._find_service(name)
        created = service is None
        if created:
            service = Service(
                tenant_id=self.tenant_id,
                name=name.strip(),
                price=price if price is not None else 0,
                duration=duration if duration is not None else 60,
                material_cost=material_cost if material_cost is not None else 0,
                cost_price=cost_price if cost_price is not None else 0,
                category=category,
                description=description,
                is_active=True if is_active is None else is_active,
            )
            self.db.add(service)
        else:
            if price is not None:
                service.price = price
            if duration is not None:
                service.duration = duration
            if category is not None:
                service.category = category
            if material_cost is not None:
                service.material_cost = material_cost
            if cost_price is not None:
                service.cost_price = cost_price
            if description is not None:
                service.description = description
            if is_active is not None:
                service.is_active = is_active
        await self.db.commit()
        await self.db.refresh(service)
        return {
            "ok": True,
            "created": created,
            "service": {
                "id": service.id,
                "name": service.name,
                "price": float(service.price or 0),
                "duration": int(service.duration or 0),
                "material_cost": float(service.material_cost or 0),
                "cost_price": float(service.cost_price or 0),
                "category": service.category,
                "is_active": bool(service.is_active),
            },
        }

    async def set_service_active(self, name: str, is_active: bool, **_kwargs) -> dict:
        """Включить/выключить услугу (мягкое удаление)."""
        service = await self._find_service(name)
        if service is None:
            return {"ok": False, "error": f"Услуга не найдена: {name}"}
        service.is_active = bool(is_active)
        await self.db.commit()
        return {"ok": True, "service_id": service.id, "name": service.name, "is_active": service.is_active}

    async def upsert_box(
        self,
        name: str,
        color: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
        **_kwargs,
    ) -> dict:
        """Создать бокс по имени или обновить существующий (переданные поля)."""
        box = await self._find_box(name)
        created = box is None
        if created:
            box = Box(
                tenant_id=self.tenant_id,
                name=name.strip(),
                color=color,
                sort_order=sort_order if sort_order is not None else 0,
                is_active=True if is_active is None else is_active,
            )
            self.db.add(box)
        else:
            if color is not None:
                box.color = color
            if sort_order is not None:
                box.sort_order = sort_order
            if is_active is not None:
                box.is_active = is_active
        await self.db.commit()
        await self.db.refresh(box)
        return {
            "ok": True,
            "created": created,
            "box": {
                "id": box.id,
                "name": box.name,
                "color": box.color,
                "sort_order": box.sort_order,
                "is_active": bool(box.is_active),
            },
        }

    async def upsert_discount(
        self,
        name: str,
        type: str,
        discount_percent: int,
        slot_start: str | None = None,
        slot_end: str | None = None,
        service_id: int | None = None,
        valid_until: str | None = None,
        is_active: bool | None = None,
        **_kwargs,
    ) -> dict:
        """Создать правило скидки по имени или обновить существующее."""
        if type not in DISCOUNT_TYPES:
            return {"ok": False, "error": f"Неизвестный тип скидки: {type}. Доступно: {', '.join(DISCOUNT_TYPES)}"}
        if not 0 <= int(discount_percent) <= 100:
            return {"ok": False, "error": "discount_percent должен быть 0–100"}

        rule = await self._find_discount(name)
        created = rule is None
        if created:
            rule = DiscountRule(
                tenant_id=self.tenant_id,
                name=name.strip(),
                type=type,
                conditions={},
                discount_percent=int(discount_percent),
                slot_start=_parse_time(slot_start),
                slot_end=_parse_time(slot_end),
                service_id=service_id,
                valid_until=_parse_valid_until(valid_until),
                is_active=True if is_active is None else is_active,
            )
            self.db.add(rule)
        else:
            rule.type = type
            rule.discount_percent = int(discount_percent)
            if slot_start is not None:
                rule.slot_start = _parse_time(slot_start)
            if slot_end is not None:
                rule.slot_end = _parse_time(slot_end)
            if service_id is not None:
                rule.service_id = service_id
            if valid_until is not None:
                rule.valid_until = _parse_valid_until(valid_until)
            if is_active is not None:
                rule.is_active = is_active
        await self.db.commit()
        await self.db.refresh(rule)
        return {
            "ok": True,
            "created": created,
            "discount": {
                "id": rule.id,
                "name": rule.name,
                "type": rule.type,
                "discount_percent": rule.discount_percent,
                "slot_start": rule.slot_start.strftime("%H:%M") if rule.slot_start else None,
                "slot_end": rule.slot_end.strftime("%H:%M") if rule.slot_end else None,
                "is_active": bool(rule.is_active),
            },
        }

    async def create_master(
        self,
        full_name: str,
        phone: str,
        password: str,
        commission_percent: int = 0,
        **_kwargs,
    ) -> dict:
        """Завести нового мастера (логин по телефону)."""
        existing = await self.db.execute(select(User).where(User.phone == phone))
        if existing.scalar_one_or_none() is not None:
            return {"ok": False, "error": f"Пользователь с телефоном {phone} уже существует"}
        master = User(
            tenant_id=self.tenant_id,
            phone=phone,
            password=hash_password(password),
            full_name=full_name.strip(),
            role="master",
            commission_percent=int(commission_percent or 0),
        )
        self.db.add(master)
        await self.db.commit()
        await self.db.refresh(master)
        return {"ok": True, "master": {"id": master.id, "name": master.full_name, "phone": master.phone}}


# Имя функции в промпте → метод AdminTools
HANDLERS = {
    "list_services": "list_services",
    "list_boxes": "list_boxes",
    "list_discounts": "list_discounts",
    "list_staff": "list_staff",
    "upsert_service": "upsert_service",
    "set_service_active": "set_service_active",
    "upsert_box": "upsert_box",
    "upsert_discount": "upsert_discount",
    "create_master": "create_master",
}


async def dispatch(tools: AdminTools, name: str, arguments: dict) -> dict:
    """Вызвать функцию промпта по имени. Неизвестная функция → ошибка модели."""
    method_name = HANDLERS.get(name)
    if method_name is None:
        return {"ok": False, "error": f"Функция '{name}' не поддерживается."}
    method = getattr(tools, method_name)
    return await method(**(arguments or {}))
