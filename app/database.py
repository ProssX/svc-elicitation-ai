"""
Database Configuration Module
Manages PostgreSQL connection, session factory, and dependency injection for FastAPI
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    echo=settings.app_env == "development",
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    FastAPI dependency for database sessions.
    Provides an async database session with automatic commit/rollback.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def validate_database_connection() -> bool:
    """
    Validate database connection during application startup.
    Returns True if connection is successful, False otherwise.
    """
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection validated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def close_database_connection():
    """
    Close database connection pool during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connection pool closed")
