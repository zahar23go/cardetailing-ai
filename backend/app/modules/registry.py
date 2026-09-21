"""Реестр модулей: тариф может отключить домен через ENABLED_MODULES."""
from __future__ import annotations

from importlib import import_module

from fastapi import FastAPI

from app.core.config import settings

# Порядок: ядро первым, опциональные домены дальше.
MODULE_ORDER = [
    "core",
    "services",
    "appointments",
    "cars",
    "photos",
    "materials",
    "tech_cards",
    "inventory",
    "tech_analytics",
    "expenses",
    "analytics",
    "ai",
    "reviews",
    "discounts",
    "notifications",
    "payments",
]


def _enabled() -> set[str] | None:
    raw = (settings.ENABLED_MODULES or "all").strip()
    if raw.lower() == "all":
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def enabled_module_names() -> list[str]:
    """Список доменов, которые монтируются при текущем ENABLED_MODULES."""
    enabled = _enabled()
    if enabled is None:
        return list(MODULE_ORDER)
    names = ["core"]
    for name in MODULE_ORDER:
        if name != "core" and name in enabled:
            names.append(name)
    return names


def include_modules(app: FastAPI) -> None:
    enabled = _enabled()
    for name in MODULE_ORDER:
        if enabled is not None and name not in enabled and name != "core":
            print(f"[modules] skip {name}")
            continue
        try:
            mod = import_module(f"app.modules.{name}.router")
        except ModuleNotFoundError:
            print(f"[modules] no router for {name}")
            continue
        router = getattr(mod, "router", None)
        if router is None:
            continue
        app.include_router(router)
        print(f"[modules] mounted {name}")
