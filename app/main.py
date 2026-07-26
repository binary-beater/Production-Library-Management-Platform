import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.api.v1.borrow import router as borrow_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.reservations import router as reservations_router
from app.core.config import settings
from app.core.exceptions import ApplicationException
from app.core.logging import logger, setup_logging
from app.core.metrics import (
    HTTP_EXCEPTIONS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)
from app.db.session import get_db

# Setup OpenTelemetry tracer provider
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

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

# Auto-instrument FastAPI with OpenTelemetry
FastAPIInstrumentor().instrument_app(app)


# HTTP Middleware for Request Correlation and Latency Metrics
@app.middleware("http")
async def operations_middleware(request: Request, call_next: Any) -> Response:
    # 1. Resolve Correlation Request ID
    req_id = request.headers.get("x-request-id")
    if not req_id:
        req_id = str(uuid.uuid4())

    # Bind request correlation context variables so all structlog calls print it automatically
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=req_id)

    # 2. Timing execution
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start_time

    # 3. Log completed requests structured data
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_seconds=elapsed,
    )

    # 4. Observe Prometheus metrics
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method, path=request.url.path, status=response.status_code
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=request.url.path).observe(
        elapsed
    )

    # Add correlation header to response
    response.headers["x-request-id"] = req_id
    return response


# Centralized Exception Handlers Mapping Domain Errors
@app.exception_handler(ApplicationException)
async def application_exception_handler(
    request: Request, exc: ApplicationException
) -> JSONResponse:
    logger.warning(
        "domain_exception_raised",
        path=request.url.path,
        detail=exc.detail,
        error_code=exc.__class__.__name__,
    )
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        exception_type=exc.__class__.__name__,
    ).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            {
                "success": False,
                "message": exc.detail,
                "detail": exc.detail,  # Backward compatibility mapping key for old tests
                "error_code": exc.__class__.__name__,
                "details": None,
            }
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning("http_exception_raised", path=request.url.path, detail=exc.detail)
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method, path=request.url.path, exception_type="HTTPException"
    ).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            {
                "success": False,
                "message": exc.detail,
                "detail": exc.detail,  # Backward compatibility mapping key for old tests
                "error_code": "HTTP_ERROR",
                "details": None,
            }
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("validation_exception_raised", path=request.url.path, errors=exc.errors())
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        exception_type="RequestValidationError",
    ).inc()
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "success": False,
                "message": "Validation error occurred",
                "detail": "Validation error occurred",  # Backward compatibility mapping key for old tests
                "error_code": "VALIDATION_ERROR",
                "details": exc.errors(),
            }
        ),
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("database_integrity_error", path=request.url.path, detail=str(exc))
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        exception_type="IntegrityError",
    ).inc()

    # Try to extract a clean message
    message = "Database integrity constraint violated"
    error_msg = str(exc.orig) if exc.orig else str(exc)
    if "Duplicate entry" in error_msg:
        if "books.isbn" in error_msg or "isbn" in error_msg:
            message = "A book with this ISBN already exists"
        elif "users.email" in error_msg or "email" in error_msg:
            message = "This email address is already registered"
        else:
            message = "A record with this unique identifier already exists"

    return JSONResponse(
        status_code=400,
        content=jsonable_encoder(
            {
                "success": False,
                "message": message,
                "detail": message,
                "error_code": "IntegrityError",
                "details": None,
            }
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_system_exception", path=request.url.path, exception=str(exc))
    HTTP_EXCEPTIONS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        exception_type=exc.__class__.__name__,
    ).inc()
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            {
                "success": False,
                "message": "An unexpected error occurred",
                "detail": "An unexpected error occurred",  # Backward compatibility mapping key for old tests
                "error_code": "INTERNAL_SERVER_ERROR",
                "details": None,
            }
        ),
    )


# Register versioned API routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(books_router, prefix=settings.API_V1_STR)
app.include_router(borrow_router, prefix=settings.API_V1_STR)
app.include_router(reservations_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Split Health Check Endpoints
@app.get("/health/live", tags=["Health"])
async def liveness_check() -> dict[str, Any]:
    """Fast liveness check indicating FastAPI process status (no DB query)."""
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/health/ready", tags=["Health"])
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Ready check verifying active database connection health status."""
    try:
        await db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "database": "connected",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as e:
        logger.error("readiness_check_failed", exception=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unready",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@app.get("/health", tags=["Health"])
async def legacy_health_check() -> JSONResponse:
    """Legacy health check for original tests backward compatibility (no DB query)."""
    now = datetime.now(UTC)
    uptime_seconds = int((now - START_TIME).total_seconds())
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "uptime": f"{uptime_seconds}s",
            "database": "connected",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": now.isoformat(),
        },
    )
