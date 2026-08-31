"""
Database Connection and Session Management.

PostgreSQL connection using SQLAlchemy with async support.
Supports SQLite for testing (aiosqlite).
"""

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
    """Bring schema to head without nesting asyncio.run() inside uvicorn.

    `alembic upgrade` via env.py uses asyncio.run(); that deadlocks the
    server loop on Windows + asyncpg, so login never gets an answer.
    """
    if _is_sqlite:
        print("[OK] SQLite: skip Alembic on startup")
        return

    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    heads = set(script.get_heads())

    async with engine.connect() as conn:
        try:
            rows = await conn.execute(text("select version_num from alembic_version"))
            current = {row[0] for row in rows}
        except Exception as exc:
            print(f"[WARN] Cannot read alembic_version ({exc}); skip auto-migrate")
            return

    if current == heads:
        print(f"[OK] Alembic at head ({', '.join(sorted(heads))})")
        return

    import subprocess
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[2]
    print(f"[..] Migrating {current or '-'} -> {heads}")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("[WARN] alembic upgrade failed; starting anyway")
        return
    print("[OK] Alembic migrations applied (upgrade head)")


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
