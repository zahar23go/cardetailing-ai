"""
CarDetailing AI — FastAPI entry.

Lifespan, CORS, static files, module routers.
Endpoint logic lives in app.modules.<name>.router
"""

import contextlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.auth import create_token as _create_token
from app.core.auth import hash_password as _hash_password
from app.core.config import settings
from app.core.database import async_session_maker, init_db
from app.core.deepseek_client import (
    get_ai_response,
    get_consultant_response,
    get_financier_response,
)
from app.models import Tenant, User
from app.modules.registry import include_modules
from app.core.plan_gate import TenantPlanMiddleware
from app.core.reminder_scheduler import start_reminder_scheduler, stop_reminder_scheduler

__all__ = [
    "app",
    "_hash_password",
    "_create_token",
    "get_ai_response",
    "get_consultant_response",
    "get_financier_response",
]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Только id — полный Tenant в сессии тянет cascade-коллекции при commit/close
    # и на Windows/asyncpg старт может навсегда зависнуть: логин не отвечает.
    async with async_session_maker() as db:
        tenant_id = (await db.execute(select(Tenant.id).limit(1))).scalar_one_or_none()
        if tenant_id is None:
            tenant = Tenant(name="Default Workshop", subdomain="default")
            db.add(tenant)
            await db.flush()
            tenant_id = tenant.id
            print("[OK] Default tenant created")
        admin_id = (
            await db.execute(select(User.id).where(User.phone == "+79999999999"))
        ).scalar_one_or_none()
        if admin_id is None:
            db.add(
                User(
                    phone="+79999999999",
                    password=_hash_password("admin123"),
                    full_name="Super Admin",
                    role="super_admin",
                    tenant_id=tenant_id,
                )
            )
            print("[OK] Super-admin created (phone: +79999999999, password: admin123)")
        else:
            print("[OK] Super-admin already exists")
        await db.commit()
    start_reminder_scheduler()
    print("[OK] Application ready")
    try:
        yield
    finally:
        await stop_reminder_scheduler()


app = FastAPI(title="CarDetailing AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantPlanMiddleware)

uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
if os.path.isdir(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "CarDetailing AI is running!"}


include_modules(app)
