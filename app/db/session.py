import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import os

from app.core.config import settings

logger = logging.getLogger("math_gap.db")

db_url = settings.database_url

# Automatic fallback to SQLite if Postgres url is missing or seems unconfigured
if not db_url or "postgresql" not in db_url:
    db_url = "sqlite+aiosqlite:///math_gap.db"

if "sqlite" in db_url:
    logger.info("Using SQLite database: %s", db_url)
    engine = create_async_engine(db_url)
else:
    logger.info("Using PostgreSQL database engine")
    try:
        engine = create_async_engine(db_url, pool_pre_ping=True)
    except Exception as exc:
        logger.warning("Failed to connect to PostgreSQL. Falling back to SQLite. Error: %s", exc)
        db_url = "sqlite+aiosqlite:///math_gap.db"
        engine = create_async_engine(db_url)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


