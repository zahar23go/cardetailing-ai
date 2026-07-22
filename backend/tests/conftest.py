"""
Test configuration for CarDetailing AI.

Uses async SQLite for test isolation.
All PostgreSQL-specific types (UUID, JSONB) are patched
to work with SQLite via @compiles decorators.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID, uuid4

import bcrypt
import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# =========================================================================
# Patch PostgreSQL types for SQLite — MUST run BEFORE app model imports
# =========================================================================
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(FunctionElement, "sqlite")
def sqlite_compile_function(element, compiler, **kw):
    """Replace PostgreSQL gen_random_uuid() with SQLite equivalent."""
    if element.name == "gen_random_uuid":
        return "(lower(hex(randomblob(16))))"
    return compiler.visit_function(element)


# =========================================================================
# Now import the app
# =========================================================================
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force test DB URL before settings is called
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

from app.main import app, _hash_password, _create_token
from app.core.database import Base, get_db
from app.models import Box, Tenant, User, UserRole, Service, Car, Appointment, AppointmentStatus, DiscountRule, Expense, Photo, EntityType, WorkingHours, AppointmentHistory, Payment, LoyaltyTierConfig
from app.core.image_service import validate_image, save_file_local, generate_filename

# =========================================================================
# Test database engine
# =========================================================================
TEST_DB_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test and drop them after.
    
    This ensures complete test isolation — no data leaks between tests.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with overridden DB dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def default_tenant(db_session: AsyncSession) -> Tenant:
    """Create the default tenant (needed for users and services)."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Workshop",
        subdomain="test",
        config={},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, default_tenant: Tenant) -> User:
    """Create a test client user with known credentials."""
    hashed = _hash_password("testpass123")
    user = User(
        phone="+79991112233",
        password=hashed,
        full_name="Тестовый Клиент",
        role="client",
        tenant_id=default_tenant.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_master(db_session: AsyncSession, default_tenant: Tenant) -> User:
    """Create a test master user."""
    hashed = _hash_password("masterpass123")
    user = User(
        phone="+79991112244",
        password=hashed,
        full_name="Тестовый Мастер",
        role="master",
        tenant_id=default_tenant.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession, default_tenant: Tenant) -> User:
    """Create a test admin user."""
    hashed = _hash_password("adminpass123")
    user = User(
        phone="+79991112255",
        password=hashed,
        full_name="Тестовый Админ",
        role="admin",
        tenant_id=default_tenant.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """Generate a valid JWT token for the test client user."""
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest_asyncio.fixture
async def admin_token(test_admin: User) -> str:
    """Generate a valid JWT token for the admin user."""
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": str(test_admin.id),
        "tenant_id": str(test_admin.tenant_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    """Return authorization headers with the client token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_token: str) -> dict:
    """Return authorization headers with the admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def test_service(db_session: AsyncSession, default_tenant: Tenant) -> Service:
    """Create a test service."""
    service = Service(
        name="Полировка кузова",
        description="Полная полировка кузова",
        category="Детейлинг",
        price=5000.00,
        duration=120,
        material_cost=500.00,
        is_active=True,
        tenant_id=default_tenant.id,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


@pytest_asyncio.fixture
async def test_car(db_session: AsyncSession, default_tenant: Tenant, test_user: User) -> Car:
    """Create a test car belonging to the test user."""
    car = Car(
        client_id=test_user.id,
        tenant_id=default_tenant.id,
        make="BMW",
        model="X5",
        year=2024,
        license_plate="А123БВ777",
        color="Чёрный",
    )
    db_session.add(car)
    await db_session.commit()
    await db_session.refresh(car)
    return car
