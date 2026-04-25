"""Database configuration and session management."""

import urllib.parse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


def _get_db_name_from_url(url: str) -> str:
    """Extract database name from PostgreSQL URL."""
    parsed = urllib.parse.urlparse(url)
    return parsed.path.lstrip("/")


def create_database_if_not_exists():
    """Create PostgreSQL database if it does not exist (sync, using psycopg2)."""
    db_name = _get_db_name_from_url(settings.SYNC_DATABASE_URL)
    # Connect to the default 'postgres' maintenance database
    parsed = urllib.parse.urlparse(settings.SYNC_DATABASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""

    conn = psycopg2.connect(
        dbname="postgres",
        host=host,
        port=port,
        user=user,
        password=password,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,),
            )
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{db_name}"')
                print(f'Created database "{db_name}"')
            else:
                print(f'Database "{db_name}" already exists')
    finally:
        conn.close()


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database: create if missing, then create tables."""
    create_database_if_not_exists()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
