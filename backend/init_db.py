"""
Database initialization script.

Creates all tables defined in app.models.
Run: python init_db.py
"""

import asyncio

# Import all models so they register on Base.metadata
import app.models  # noqa: F401
from app.core.database import init_db


async def main() -> None:
    print("Creating database tables...")
    await init_db()
    print("Done — all tables created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
