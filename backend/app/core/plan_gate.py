"""HTTP-гейт тарифа: 403, если домен или фича выключены планом салона."""
from __future__ import annotations

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import async_session_maker
from app.modules.plans import api_requirement, is_requirement_allowed, load_tenant_plan, normalize_plan

SKIP_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/uploads",
    "/api/login",
    "/api/register",
    "/api/plans",
    "/api/modules",
    "/api/me",
    "/api/tenants",
    "/api/pwa",
)


class TenantPlanMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in SKIP_PREFIXES):
            return await call_next(request)
        req = api_requirement(path)
        if req is None:
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return await call_next(request)
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        except jwt.PyJWTError:
            return await call_next(request)
        tenant_id = payload.get("tenant_id")
        async with async_session_maker() as db:
            plan = await load_tenant_plan(db, tenant_id)
        if is_requirement_allowed(req, plan):
            return await call_next(request)
        label = { "basic": "Базовый", "pro": "Про", "business": "Бизнес" }.get(
            normalize_plan(plan), "текущем"
        )
        return JSONResponse(
            status_code=403,
            content={"detail": f"Раздел недоступен на тарифе {label}."},
        )
