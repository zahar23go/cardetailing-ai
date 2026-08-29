"""Коммерческие тарифы салона: Базовый / Про / Бизнес.

Роутеры по-прежнему монтируются через ENABLED_MODULES (инстанс).
Какой салон что видит — поле tenants.plan, не env.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

PLAN_BASIC = "basic"
PLAN_PRO = "pro"
PLAN_BUSINESS = "business"
PLAN_IDS = (PLAN_BASIC, PLAN_PRO, PLAN_BUSINESS)
DEFAULT_PLAN = PLAN_BUSINESS

PWA_DEFAULT_NAME = "CAR DETAILING AI"
PWA_DEFAULT_SHORT = "Detailing AI"
PWA_DEFAULT_ICON = "/icons/icon-192x192.png"
PWA_THEME = "#C8A977"
PWA_BG = "#0B0D10"

BASIC_MODULES = [
    "core",
    "services",
    "appointments",
    "cars",
    "photos",
    "materials",
    "discounts",
    "notifications",
]

PRO_MODULES = BASIC_MODULES + [
    "ai",
    "analytics",
    "expenses",
    "tech_cards",
    "payments",
]

BUSINESS_MODULES = [
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
    "discounts",
    "notifications",
    "payments",
]

PLANS: dict[str, dict] = {
    PLAN_BASIC: {
        "id": PLAN_BASIC,
        "label": "Базовый",
        "price": 2990,
        "appointment_limit": 150,
        "modules": list(BASIC_MODULES),
        "features": {"financier": False, "branding": False},
        "blurb": "До 150 записей в месяц. Услуги, запись, склад, ручные скидки. Без AI и бренда.",
    },
    PLAN_PRO: {
        "id": PLAN_PRO,
        "label": "Про",
        "price": 5990,
        "appointment_limit": None,
        "modules": list(PRO_MODULES),
        "features": {"financier": False, "branding": False},
        "blurb": "Безлимит, Детейлер, аналитика, CRM, автоскидки, портфолио. Без финансиста и White Label.",
    },
    PLAN_BUSINESS: {
        "id": PLAN_BUSINESS,
        "label": "Бизнес",
        "price": 14990,
        "appointment_limit": None,
        "modules": list(BUSINESS_MODULES),
        "features": {"financier": True, "branding": True},
        "blurb": "Финансист, White Label, расширенный склад, Excel/PDF.",
    },
}

# Более длинные префиксы первыми.
API_PREFIX_MODULE: list[tuple[str, str]] = [
    ("/api/ai/financier", "feature:financier"),
    ("/api/ai", "ai"),
    ("/api/analytics", "analytics"),
    ("/api/expenses", "expenses"),
    ("/api/discounts", "discounts"),
    ("/api/materials", "materials"),
    ("/api/inventory", "inventory"),
    ("/api/tech-cards", "tech_cards"),
    ("/api/tech-analytics", "tech_analytics"),
    ("/api/photos", "photos"),
    ("/api/upload", "photos"),
    ("/api/payments", "payments"),
    ("/api/notifications", "notifications"),
    ("/api/appointments", "appointments"),
    ("/api/boxes", "appointments"),
    ("/api/calendar", "appointments"),
    ("/api/masters", "appointments"),
    ("/api/services", "services"),
    ("/api/cars", "cars"),
]


def normalize_plan(value: str | None) -> str:
    raw = (value or DEFAULT_PLAN).strip().lower()
    if raw in PLANS:
        return raw
    return DEFAULT_PLAN


def env_module_allowlist() -> set[str] | None:
    raw = (settings.ENABLED_MODULES or "all").strip()
    if raw.lower() == "all":
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def modules_for_plan(plan: str | None) -> list[str]:
    spec = PLANS[normalize_plan(plan)]
    names: list[str] = ["core"]
    allow = env_module_allowlist()
    for name in spec["modules"]:
        if name == "core":
            continue
        if allow is not None and name not in allow:
            continue
        if name not in names:
            names.append(name)
    return names


def features_for_plan(plan: str | None) -> dict[str, bool]:
    return dict(PLANS[normalize_plan(plan)]["features"])


def catalog() -> list[dict]:
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "price": p["price"],
            "appointment_limit": p["appointment_limit"],
            "modules": list(p["modules"]),
            "features": dict(p["features"]),
            "blurb": p["blurb"],
        }
        for p in PLANS.values()
    ]


def pwa_for_tenant(tenant) -> dict:
    """White Label на тарифе Бизнес: имя и иконка салона. Иначе бренд платформы."""
    plan = normalize_plan(getattr(tenant, "plan", None) if tenant is not None else None)
    branding = bool(features_for_plan(plan).get("branding"))
    if tenant is not None and branding:
        name = (getattr(tenant, "name", None) or PWA_DEFAULT_NAME).strip() or PWA_DEFAULT_NAME
        icon = (getattr(tenant, "logo_url", None) or "").strip() or PWA_DEFAULT_ICON
        short = name if len(name) <= 12 else name[:12].rstrip()
        return {
            "name": name,
            "short_name": short,
            "icon": icon,
            "theme_color": PWA_THEME,
            "background_color": PWA_BG,
            "white_label": True,
        }
    return {
        "name": PWA_DEFAULT_NAME,
        "short_name": PWA_DEFAULT_SHORT,
        "icon": PWA_DEFAULT_ICON,
        "theme_color": PWA_THEME,
        "background_color": PWA_BG,
        "white_label": False,
    }


def web_manifest(pwa: dict, start_url: str = "/") -> dict:
    icon = pwa.get("icon") or PWA_DEFAULT_ICON
    return {
        "name": pwa["name"],
        "short_name": pwa["short_name"],
        "description": "Запись, кабинет и AI-диспетчер автомойки",
        "start_url": start_url,
        "scope": "/",
        "display": "standalone",
        "background_color": pwa.get("background_color") or PWA_BG,
        "theme_color": pwa.get("theme_color") or PWA_THEME,
        "orientation": "portrait",
        "icons": [
            {"src": icon, "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": icon if pwa.get("white_label") else "/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


def plan_payload(plan: str | None) -> dict:
    pid = normalize_plan(plan)
    spec = PLANS[pid]
    return {
        "modules": modules_for_plan(pid),
        "plan": pid,
        "plan_label": spec["label"],
        "price": spec["price"],
        "appointment_limit": spec["appointment_limit"],
        "features": features_for_plan(pid),
    }


def api_requirement(path: str) -> str | None:
    for prefix, req in API_PREFIX_MODULE:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            return req
    return None


def is_requirement_allowed(req: str, plan: str | None) -> bool:
    pid = normalize_plan(plan)
    if req.startswith("feature:"):
        key = req.split(":", 1)[1]
        return bool(features_for_plan(pid).get(key))
    return req in modules_for_plan(pid)


async def load_tenant(db: AsyncSession, tenant_id: str | UUID | None):
    if not tenant_id:
        return None
    from app.models import Tenant

    try:
        tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(Tenant).where(Tenant.id == tid))
    return result.scalar_one_or_none()


async def load_tenant_plan(db: AsyncSession, tenant_id: str | UUID | None) -> str:
    tenant = await load_tenant(db, tenant_id)
    if tenant is None:
        return DEFAULT_PLAN
    return normalize_plan(getattr(tenant, "plan", None))


async def modules_payload(db: AsyncSession, tenant_id: str | UUID | None) -> dict:
    tenant = await load_tenant(db, tenant_id)
    plan = normalize_plan(getattr(tenant, "plan", None) if tenant is not None else None)
    payload = plan_payload(plan)
    pwa = pwa_for_tenant(tenant)
    payload["pwa"] = pwa
    payload["tenant_name"] = getattr(tenant, "name", None) if tenant is not None else None
    payload["logo_url"] = getattr(tenant, "logo_url", None) if tenant is not None else None
    from app.models import Appointment

    used = 0
    limit = payload["appointment_limit"]
    if tenant_id and limit:
        try:
            tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
        except (ValueError, TypeError):
            tid = None
        if tid:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            cnt = await db.execute(
                select(func.count()).select_from(Appointment).where(
                    Appointment.tenant_id == tid,
                    Appointment.start_time >= month_start,
                    Appointment.status != "cancelled",
                )
            )
            used = int(cnt.scalar() or 0)
    payload["appointments_this_month"] = used
    return payload


async def ensure_appointment_quota(
    db: AsyncSession,
    tenant_id: UUID,
    slot_start: datetime,
) -> None:
    from fastapi import HTTPException

    plan = await load_tenant_plan(db, tenant_id)
    limit = PLANS[plan]["appointment_limit"]
    if not limit:
        return
    month_start = slot_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from app.models import Appointment

    cnt = await db.execute(
        select(func.count()).select_from(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= month_start,
            Appointment.status != "cancelled",
        )
    )
    used = int(cnt.scalar() or 0)
    if used >= int(limit):
        raise HTTPException(
            status_code=403,
            detail=f"Лимит тарифа Базовый: {limit} записей в месяц. Перейдите на Про.",
        )
