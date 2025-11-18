"""
Test configuration and fixtures
"""
import pytest
import pytest_asyncio
import asyncio
import os
import uuid
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import declarative_base
from sqlalchemy import TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from dotenv import load_dotenv

# Load test environment variables before anything else
test_env_path = Path(__file__).parent.parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)


# Custom UUID type that works with both PostgreSQL and SQLite
class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


# Create a separate Base for testing to avoid importing app.database
Base = declarative_base()

# Import models after Base is defined
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the database Base and UUID type before importing models
import app.database
app.database.Base = Base

# Patch the UUID import in db_models
import sqlalchemy.dialects.postgresql
original_uuid = sqlalchemy.dialects.postgresql.UUID
sqlalchemy.dialects.postgresql.UUID = lambda as_uuid=True: UUID()

from app.models.db_models import Interview, InterviewMessage

# Restore original UUID
sqlalchemy.dialects.postgresql.UUID = original_uuid


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    # Clean up pending tasks
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create an in-memory SQLite database engine for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up - ensure proper disposal
    try:
        await engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing"""
    async_session = async_sessionmaker(
        db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            try:
                await session.rollback()
                await session.close()
            except Exception:
                pass


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db_connections():
    """Cleanup database connections after each test to prevent asyncpg errors"""
    yield
    # After test completes, ensure all connections are properly closed
    try:
        from app.database import engine
        # Dispose and recreate the connection pool to ensure clean state
        await engine.dispose()
    except Exception:
        pass