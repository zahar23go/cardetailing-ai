"""Заглушки функций финансового ассистента (prompts/financier.yaml).

Промпт финансиста пишется отдельно; пока функции возвращают mock-данные,
чтобы проверялась вся цепочка prompt_loader → chat_service → dispatch.
Сигнатура ``FinancierTools`` совпадает с ``DetailerTools`` (drop-in для chat_service).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class FinancierTools:
    """Диспетчер функций финансиста (mock-данные до появления реального промпта)."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, client: dict, tz_offset: int = 0):
        self.db = db
        self.tenant_id = tenant_id
        self.client = client
        self.tz_offset = tz_offset

    async def get_kpi(self, **_kwargs) -> dict:
        return {"revenue": 0, "occupancy": 0, "retention": 0}

    async def get_revenue_breakdown(self, **_kwargs) -> dict:
        return {"services": [], "masters": [], "days": []}

    async def get_occupancy(self, **_kwargs) -> dict:
        return {"salon": 0, "masters": []}

    async def get_customer_retention(self, **_kwargs) -> dict:
        return {"cohorts": []}

    async def forecast(self, **_kwargs) -> dict:
        return {"revenue": 0, "occupancy": 0}


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
