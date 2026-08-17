"""
Main FastAPI application for VeriClaim AI MVP backend.

Builds the application, installs middleware and exception handlers, and manages
the database engine across the application lifespan.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import (
    DatabaseNotConfigured,
    close_async_engine,
    init_async_engine,
    test_async_connection,
)
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.services.job_queue import analysis_queue

# Configure logging before creating logger
configure_logging()
logger = get_logger(__name__)

TAGS_METADATA = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Root", "description": "Service metadata."},
    {"name": "Claims", "description": "Claim submission, retrieval, and status."},
    {"name": "Evidence", "description": "Document and image uploads for a claim."},
    {"name": "Assessment", "description": "AI analysis and its results."},
    {"name": "Decisions", "description": "Human review outcomes."},
    {"name": "Analytics", "description": "Aggregate claim metrics."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    The database is treated as optional at startup so the API can still serve
    frontend development and demo mode before Supabase credentials are in
    place; `/health` reports the real state.

    Args:
        app: FastAPI application instance.

    Yields:
        Control to the application.
    """
    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
        extra={
            "extra_fields": {
                "environment": "development" if settings.debug else "production",
                "demo_mode": settings.demo_mode,
            }
        },
    )

    app.state.db_ready = False
    try:
        await init_async_engine()
        app.state.db_ready = await test_async_connection()
        if app.state.db_ready:
            logger.info("Database connection established")
        else:
            logger.warning("Database engine created but the connection test failed")
    except DatabaseNotConfigured as exc:
        logger.warning("Database not configured: %s", exc)
        logger.info("Set DATABASE_URL in .env to enable persistence")
    except Exception:
        logger.exception("Failed to initialise the database engine")

    if not settings.supabase_jwt_secret:
        logger.warning(
            "SUPABASE_JWT_SECRET is not set; authenticated routes will reject all requests"
        )
    if not settings.supabase_service_role_key:
        logger.warning(
            "SUPABASE_SERVICE_ROLE_KEY is not set; file uploads will be unavailable"
        )

    # Workers need a usable database; without one every job would fail on pickup.
    if app.state.db_ready:
        await analysis_queue.start()
    else:
        logger.warning("Analysis workers not started: no database connection")

    logger.info("Application ready")

    yield

    logger.info("Shutting down")
    try:
        # Stop accepting work before the engine goes, so no job loses its
        # session mid-flight.
        await analysis_queue.stop()
    except Exception:
        logger.exception("Error while stopping analysis workers")
    try:
        await close_async_engine()
    except Exception:
        logger.exception("Error while closing database connections")
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered motor insurance claims processing system",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        # Deliberately not `debug=settings.debug`. Starlette's debug mode returns
        # a full traceback to the client for unhandled errors, which would both
        # bypass the handlers registered below and disclose internals. Verbosity
        # belongs in the logs; `settings.debug` still controls those.
    )

    # Added first so it sits inside CORS: error responses still get CORS headers.
    app.add_middleware(RequestContextMiddleware)

    # Explicit origins rather than "*", because the frontend sends credentials
    # and browsers reject a wildcard origin on credentialed requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=["X-Total-Count", "X-Total-Pages", REQUEST_ID_HEADER],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Report service and database status.

        Returns:
            Status payload; `database` reflects a live connection test.
        """
        db_connected = await test_async_connection()
        return {
            "status": "healthy" if db_connected else "degraded",
            "app": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "demo_mode": settings.demo_mode,
            "database": "connected" if db_connected else "disconnected",
        }

    @app.get("/", tags=["Root"])
    async def root():
        """
        Basic API information.

        Returns:
            Service name, version, and documentation links.
        """
        return {
            "message": f"Welcome to {settings.app_name} API",
            "version": settings.app_version,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    logger.info("FastAPI application created")
    return app


app = create_app()
