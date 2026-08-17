"""
Database connection and session management for VeriClaim AI MVP.

This module provides SQLAlchemy engine configuration, session factories,
and context managers for database operations against Supabase PostgreSQL.

Two engines are maintained:

* An **async** engine (asyncpg) used by the FastAPI request path.
* A **sync** engine (psycopg2) used by Alembic migrations and utility scripts.

Supabase exposes two connection endpoints. The transaction pooler (port 6543)
multiplexes connections through PgBouncer and therefore cannot support
server-side prepared statements or client-side connection pooling; the direct
connection (port 5432) supports both. This module detects which endpoint is in
use and configures the engine accordingly.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Connection pooling and timeout settings."""

    # Client-side pool. Kept modest because Supabase caps concurrent
    # connections per project; POOL_SIZE + MAX_OVERFLOW is the ceiling.
    POOL_SIZE = 5
    MAX_OVERFLOW = 5
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 1800  # Recycle before Supabase's idle timeout.
    POOL_PRE_PING = True  # Discard connections dropped by the pooler.
    ECHO = settings.debug

    CONNECT_TIMEOUT = 10  # Seconds to establish a TCP/auth handshake.
    COMMAND_TIMEOUT = 30  # Client-side cap on a single command, in seconds.
    STATEMENT_TIMEOUT_MS = 30000  # Server-side cap on a single statement.


# Values that ship in `.env.example`; treated as "not configured yet" so the
# application can still boot for frontend work and demo mode.
_PLACEHOLDER_MARKERS = (
    "user:password@host",
    "database_name",
    "your_",
    "<password>",
    "<project-ref>",
)


class DatabaseNotConfigured(ValueError):
    """Raised when DATABASE_URL is missing or still holds placeholder values."""


def _base_url():
    """
    Parse and validate DATABASE_URL into a SQLAlchemy URL object.

    Returns:
        A `sqlalchemy.engine.URL` with any driver suffix stripped.

    Raises:
        DatabaseNotConfigured: If the URL is absent or is a placeholder.
    """
    raw = (settings.database_url or "").strip()

    if not raw:
        raise DatabaseNotConfigured(
            "DATABASE_URL is not set. Add your Supabase connection string to .env"
        )

    lowered = raw.lower()
    if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
        raise DatabaseNotConfigured(
            "DATABASE_URL still contains placeholder values. Copy the connection "
            "string from your Supabase project (Project Settings -> Database) into .env"
        )

    url = make_url(raw)

    # Normalise the legacy `postgres://` scheme and drop whichever driver the
    # operator happened to write, so we can attach the correct one per engine.
    if url.drivername.startswith("postgres"):
        url = url.set(drivername="postgresql")
    else:
        raise DatabaseNotConfigured(
            f"DATABASE_URL must be a PostgreSQL URL, got driver '{url.drivername}'"
        )

    return url


def _is_transaction_pooler(url) -> bool:
    """
    Detect Supabase's PgBouncer transaction pooler.

    Prepared statements and client-side pooling must be disabled against it.

    Args:
        url: Parsed SQLAlchemy URL.

    Returns:
        True if the URL points at the transaction pooler.
    """
    host = (url.host or "").lower()
    return url.port == 6543 or "pooler.supabase.com" in host


def get_sync_database_url() -> str:
    """
    Build the psycopg2 URL used by Alembic and utility scripts.

    Returns:
        A `postgresql+psycopg2://` connection string.
    """
    return _base_url().set(drivername="postgresql+psycopg2").render_as_string(
        hide_password=False
    )


# libpq's sslmode values mapped onto asyncpg's `ssl` argument. asyncpg has no
# `sslmode` parameter, so leaving it in the URL raises TypeError on connect.
_SSLMODE_TO_ASYNCPG = {
    "disable": False,
    "allow": "prefer",
    "prefer": "prefer",
    "require": "require",
    "verify-ca": "verify-ca",
    "verify-full": "verify-full",
}


def _split_sslmode(url):
    """
    Separate a libpq `sslmode` query parameter from an async URL.

    Args:
        url: Parsed SQLAlchemy URL.

    Returns:
        A tuple of (url without sslmode, asyncpg `ssl` value or None).
    """
    sslmode = url.query.get("sslmode")
    if sslmode is None:
        return url, None

    # A repeated query key arrives as a tuple; the last one wins, as in libpq.
    if isinstance(sslmode, (tuple, list)):
        sslmode = sslmode[-1]

    remaining = {k: v for k, v in url.query.items() if k != "sslmode"}
    ssl_value = _SSLMODE_TO_ASYNCPG.get(str(sslmode).lower())

    if ssl_value is None:
        logger.warning("Unrecognised sslmode %r; falling back to 'require'", sslmode)
        ssl_value = "require"

    return url.set(query=remaining), ssl_value


def get_async_database_url() -> str:
    """
    Build the asyncpg URL used by the FastAPI request path.

    Any `sslmode` parameter is stripped; it is applied through `connect_args`
    instead because asyncpg does not accept it as a connection keyword.

    Returns:
        A `postgresql+asyncpg://` connection string.
    """
    url, _ = _split_sslmode(_base_url())
    return url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)


def get_database_url(async_mode: bool = False) -> str:
    """
    Get the database URL for the requested driver.

    Args:
        async_mode: If True, return the asyncpg URL; otherwise psycopg2.

    Returns:
        A database connection URL.
    """
    return get_async_database_url() if async_mode else get_sync_database_url()


def _masked(url_str: str) -> str:
    """Render a URL with its password hidden, for logging."""
    try:
        return make_url(url_str).render_as_string(hide_password=True)
    except Exception:
        return "***"


def create_sync_engine():
    """
    Create the synchronous engine (psycopg2) with connection pooling.

    Returns:
        A configured SQLAlchemy `Engine`.

    Raises:
        DatabaseNotConfigured: If DATABASE_URL is unusable.
    """
    url = _base_url()
    database_url = get_sync_database_url()
    pooled = _is_transaction_pooler(url)

    logger.info("Creating synchronous database engine: %s", _masked(database_url))

    # libpq keywords: `connect_timeout` (not `timeout`) and `options`.
    connect_args = {
        "connect_timeout": DatabaseConfig.CONNECT_TIMEOUT,
        "options": f"-c statement_timeout={DatabaseConfig.STATEMENT_TIMEOUT_MS}",
    }

    if pooled:
        # PgBouncer already pools server-side; a second pool on top of it
        # only holds transaction slots open.
        return create_engine(
            database_url,
            poolclass=NullPool,
            echo=DatabaseConfig.ECHO,
            connect_args=connect_args,
        )

    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=DatabaseConfig.POOL_SIZE,
        max_overflow=DatabaseConfig.MAX_OVERFLOW,
        pool_timeout=DatabaseConfig.POOL_TIMEOUT,
        pool_recycle=DatabaseConfig.POOL_RECYCLE,
        pool_pre_ping=DatabaseConfig.POOL_PRE_PING,
        echo=DatabaseConfig.ECHO,
        connect_args=connect_args,
    )


def create_async_engine_instance() -> AsyncEngine:
    """
    Create the asynchronous engine (asyncpg) with connection pooling.

    Returns:
        A configured `AsyncEngine`.

    Raises:
        DatabaseNotConfigured: If DATABASE_URL is unusable.
    """
    url = _base_url()
    _, ssl_value = _split_sslmode(url)
    database_url = get_async_database_url()
    pooled = _is_transaction_pooler(url)

    logger.info("Creating asynchronous database engine: %s", _masked(database_url))

    # asyncpg keywords: `timeout`, `command_timeout`, `server_settings`.
    # It has no `options` parameter -- server-side GUCs go in `server_settings`.
    connect_args = {
        "timeout": DatabaseConfig.CONNECT_TIMEOUT,
        "command_timeout": DatabaseConfig.COMMAND_TIMEOUT,
        "server_settings": {
            "statement_timeout": str(DatabaseConfig.STATEMENT_TIMEOUT_MS),
            "application_name": settings.app_name,
        },
    }

    if ssl_value is not None:
        connect_args["ssl"] = ssl_value

    if pooled:
        # PgBouncer in transaction mode cannot keep prepared statements across
        # checkouts; disabling both caches avoids DuplicatePreparedStatementError.
        connect_args["statement_cache_size"] = 0
        return create_async_engine(
            database_url,
            poolclass=NullPool,
            echo=DatabaseConfig.ECHO,
            connect_args=connect_args,
        )

    # Async engines require an asyncio-aware pool; SQLAlchemy's default here is
    # AsyncAdaptedQueuePool. Passing the sync QueuePool raises ArgumentError.
    return create_async_engine(
        database_url,
        pool_size=DatabaseConfig.POOL_SIZE,
        max_overflow=DatabaseConfig.MAX_OVERFLOW,
        pool_timeout=DatabaseConfig.POOL_TIMEOUT,
        pool_recycle=DatabaseConfig.POOL_RECYCLE,
        pool_pre_ping=DatabaseConfig.POOL_PRE_PING,
        echo=DatabaseConfig.ECHO,
        connect_args=connect_args,
    )


# Synchronous engine and session factory. Built eagerly so Alembic and scripts
# can import them, but tolerant of an unconfigured database so the app still
# boots for frontend work.
try:
    sync_engine = create_sync_engine()
except DatabaseNotConfigured as exc:
    logger.warning("Sync database engine deferred: %s", exc)
    sync_engine = None

SyncSessionLocal = (
    sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)
    if sync_engine is not None
    else None
)

# Asynchronous engine and session factory, initialised during app startup.
async_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker | None = None


async def init_async_engine() -> None:
    """
    Initialise the async engine and session factory.

    Called during application startup.

    Raises:
        DatabaseNotConfigured: If DATABASE_URL is unusable.
    """
    global async_engine, AsyncSessionLocal

    async_engine = create_async_engine_instance()
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Async engine and session factory initialised")


async def close_async_engine() -> None:
    """Dispose of the async engine and close pooled connections."""
    global async_engine, AsyncSessionLocal

    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None
        AsyncSessionLocal = None
        logger.info("Async engine disposed and connections closed")


# ===== Synchronous session helpers =====


@contextmanager
def get_db_sync() -> Generator[Session, None, None]:
    """
    Context manager yielding a synchronous session.

    Commits on success and rolls back on error.

    Usage:
        with get_db_sync() as db:
            db.add(claim)

    Yields:
        A SQLAlchemy `Session`.

    Raises:
        RuntimeError: If the sync engine is not configured.
    """
    if SyncSessionLocal is None:
        raise RuntimeError(
            "Synchronous database engine not initialised. Configure DATABASE_URL in .env"
        )

    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Rolling back synchronous database session")
        raise
    finally:
        session.close()


def get_sync_session() -> Session:
    """
    Get a raw synchronous session; the caller owns its lifecycle.

    Returns:
        A SQLAlchemy `Session`.

    Raises:
        RuntimeError: If the sync engine is not configured.
    """
    if SyncSessionLocal is None:
        raise RuntimeError(
            "Synchronous database engine not initialised. Configure DATABASE_URL in .env"
        )
    return SyncSessionLocal()


# ===== Asynchronous session helpers =====


@asynccontextmanager
async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager yielding an async session.

    Commits on success and rolls back on error.

    Usage:
        async with get_db_async() as db:
            await db.execute(stmt)

    Yields:
        An `AsyncSession`.

    Raises:
        RuntimeError: If `init_async_engine()` has not run.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async engine not initialised. Call init_async_engine() during app startup."
        )

    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Rolling back asynchronous database session")
        raise
    finally:
        await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async session.

    Usage:
        @app.get("/claims")
        async def list_claims(db: AsyncSession = Depends(get_async_session)):
            ...

    Yields:
        An `AsyncSession`.

    Raises:
        RuntimeError: If `init_async_engine()` has not run.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async engine not initialised. Call init_async_engine() during app startup."
        )

    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ===== Health checks =====


def test_sync_connection() -> bool:
    """
    Verify the synchronous connection with a trivial round trip.

    Returns:
        True if the query succeeded.
    """
    if sync_engine is None:
        logger.warning("Synchronous database engine not configured")
        return False

    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Synchronous database connection test passed")
        return True
    except Exception as exc:
        logger.error("Synchronous database connection test failed: %s", exc)
        return False


async def test_async_connection() -> bool:
    """
    Verify the asynchronous connection with a trivial round trip.

    Returns:
        True if the query succeeded.
    """
    if async_engine is None:
        logger.warning("Async database engine not configured")
        return False

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Asynchronous database connection test passed")
        return True
    except Exception as exc:
        logger.error("Asynchronous database connection test failed: %s", exc)
        return False
