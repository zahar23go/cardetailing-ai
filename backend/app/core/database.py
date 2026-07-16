"""
Database Connection and Session Management.

PostgreSQL connection using SQLAlchemy with async support.
Supports SQLite for testing (aiosqlite).
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings


# Detect database type — SQLite doesn't support pool_size/max_overflow
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database session.

    The caller (endpoint) is responsible for calling commit/rollback.
    Yields:
        AsyncSession: Database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables using Alembic migrations.

    Runs `alembic upgrade head` in a thread to avoid
    event loop conflict (Alembic uses asyncio.run internally).
    """
    from alembic.config import Config
    from alembic import command

    def _run_migrations() -> None:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    await asyncio.to_thread(_run_migrations)
    print("[OK] Alembic migrations applied (upgrade head)")


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
