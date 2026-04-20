"""Database configuration and session management."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

# Database URL - PostgreSQL with async driver
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/style_transfer"

logger = logging.getLogger(__name__)

# Create async engine with NullPool to avoid "attached to a different loop" errors
# when async connections are used across different event loops (FastAPI vs Celery).
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    logger.debug("Creating new database session")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
