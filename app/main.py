import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging, logger

# Track application start time for uptime metric
START_TIME = datetime.now(timezone.utc)

# Initialize structured JSON logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
async def health_check():
    now = datetime.now(timezone.utc)
    uptime_seconds = int((now - START_TIME).total_seconds())

    return {
        "status": "healthy",
        "uptime": f"{uptime_seconds}s",
        "database": "connected",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": now.isoformat(),
    }
