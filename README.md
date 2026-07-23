# Library Management Platform (LMP)

A production-grade backend platform built with FastAPI, SQLAlchemy 2.0, Alembic, MySQL 8.0, Docker, PyTest, Keploy, OpenTelemetry, Prometheus, and GitHub Actions.

---

## 1. System Architecture & Component Diagram

```text
               Client (HTTP / REST)
                        │
             FastAPI API Routers (`app/api/v1`)
                        │
          Request Middleware & Correlation ID (`app/middleware`)
                        │
          Security Guards & Auth Dependencies (`app/security`, `app/dependencies`)
                        │
             Business Logic Service Layer (`app/services`)
                        │
             Repository Data Access Layer (`app/repositories`)
                        │
             SQLAlchemy 2.0 ORM Engine & MySQL 8.0 (`app/models`, `app/db`)
```

---

## 2. Directory Structure Standards

```text
app/
├── api/v1/         # FastAPI Routers (v1 Endpoints)
├── core/           # Config, Security utilities, Structured JSON Logger
├── db/             # SQLAlchemy Engine, SessionLocal, Base ORM
├── dependencies/   # FastAPI Dependency Injections (Auth, DB, Services)
├── exceptions/     # Centralized Exception Handlers & Custom Exceptions
├── middleware/     # Correlation ID & Request timing middleware
├── models/         # SQLAlchemy Declarative Models
├── repositories/   # Async Repository Data Access Layer
├── schemas/        # Pydantic v2 Serialization & Validation Schemas
├── services/       # Pure Business Logic Layer
└── utils/          # Pagination & Helper Utilities

tests/
├── unit/           # Service Unit Tests (Mocks)
├── integration/    # Repository & Database Integration Tests
└── api/            # End-to-End API Integration Tests

docs/
├── adr/            # Architecture Decision Records (0001 to 0015)
├── 00-vision.md
├── 01-functional-requirements.md
├── 02-non-functional-requirements.md
├── 03-architecture.md
└── repository-standards.md

metrics/            # Benchmark reports, coverage XML, evidence files
```

---

## 3. Quick Start (Local & Docker)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Running via Docker Compose
```bash
# Clone the repository
git clone <repo-url>
cd "Production Library Management Platform"

# Launch application and MySQL 8.0 container
docker compose up --build
```
- Interactive Swagger API Documentation: `http://localhost:8000/docs`
- Production Health Check Endpoint: `http://localhost:8000/health`

### Running Tests locally
```bash
# Install dependencies
pip install -e ".[dev]"

# Run full test suite with coverage report
pytest
```

---

## 4. Key Architectural Highlights
- **FastAPI Lifespan Context Manager**: Clean async startup/shutdown resource orchestration.
- **Single-Use Refresh Token Rotation**: Server-side token revocation table (`refresh_tokens`).
- **Soft Deletes**: `is_deleted` and `deleted_at` fields on catalog objects preserve referential integrity.
- **Immutable Borrow History**: Borrow state transitions (`BORROWED`, `RETURNED`, `RENEWED`, `OVERDUE`).
- **Connection Pool Hardening**: Tuned SQLAlchemy pool parameters (`pool_size=10`, `max_overflow=20`, `pool_recycle=1800`).

---

## 5. Resume Evidence & Validation
Every metric on the resume is substantiated by evidence recorded in `docs/resume-validation.md` and CI outputs in `metrics/`.
