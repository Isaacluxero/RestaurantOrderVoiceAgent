"""Database connection and session management."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.db.models import Base

logger = logging.getLogger(__name__)


# Convert postgresql:// to postgresql+asyncpg:// for async support
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_db() -> None:
    """Reset database by truncating all tables. Removes all data but keeps schema."""
    logger.info("Resetting database: truncating all tables...")
    try:
        async with engine.begin() as conn:
            # Truncate all tables in correct order (respecting foreign keys)
            # RESTART IDENTITY resets auto-increment counters
            # CASCADE handles dependent tables automatically
            await conn.execute(text("TRUNCATE TABLE order_items, orders, calls RESTART IDENTITY CASCADE"))
        logger.info("Database reset complete: all tables are now empty")
    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        # Don't raise - let the app continue even if reset fails
        # This is useful for first-time setup when tables don't exist yet


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

