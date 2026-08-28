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
    async with async_session_maker() as db:
        tenant_result = await db.execute(select(Tenant).limit(1))
        default_tenant = tenant_result.scalar_one_or_none()
        if not default_tenant:
            default_tenant = Tenant(
                name="Default Workshop",
                subdomain="default",
            )
            db.add(default_tenant)
            await db.commit()
            await db.refresh(default_tenant)
            print("[OK] Default tenant created")
        result = await db.execute(select(User).where(User.phone == "+79999999999"))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            super_admin = User(
                phone="+79999999999",
                password=_hash_password("admin123"),
                full_name="Super Admin",
                role="super_admin",
                tenant_id=default_tenant.id,
            )
            db.add(super_admin)
            await db.commit()
            print("[OK] Super-admin created (phone: +79999999999, password: admin123)")
        else:
            print("[OK] Super-admin already exists")
    yield


app = FastAPI(title="CarDetailing AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
if os.path.isdir(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "CarDetailing AI is running!"}


include_modules(app)
