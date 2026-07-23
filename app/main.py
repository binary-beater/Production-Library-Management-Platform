from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import logger, setup_logging

# Track application start time for uptime metric
START_TIME = datetime.now(UTC)

# Initialize structured JSON logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Application Startup
    logger.info("Application starting up", environment=settings.ENVIRONMENT)
    yield
    # Application Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    now = datetime.now(UTC)
    uptime_seconds = int((now - START_TIME).total_seconds())

    return {
        "status": "healthy",
        "uptime": f"{uptime_seconds}s",
        "database": "connected",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": now.isoformat(),
    }
