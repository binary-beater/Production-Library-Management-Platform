# 📚 Production Library Management Platform

[![CI](https://github.com/binary-beater/Production-Library-Management-Platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/binary-beater/Production-Library-Management-Platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Tests](https://img.shields.io/badge/Tests-68_Passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)


A production-grade backend platform built with **FastAPI**, **SQLAlchemy 2.0**, and **MySQL 8.0**. The system implements secure JWT Authentication, Single-Use Refresh Token Rotation (RTR), soft-deletions, fine calculations, and a high-concurrency FIFO hold-queue for reserving books.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI |
| **Language** | Python 3.11+ |
| **ORM** | SQLAlchemy 2.0 (Async Engine) |
| **Database** | MySQL 8.0 |
| **Validation** | Pydantic v2 |
| **Authentication** | JWT (JSON Web Tokens) |
| **Migrations** | Alembic |
| **Testing** | PyTest (with coverage tracking) |
| **Monitoring** | Prometheus Metrics |
| **Tracing** | OpenTelemetry |
| **Logging** | Structlog (Structured JSON) |
| **Containerization** | Docker & Docker Compose |

---

## ✨ Features

- **JWT Authentication**: Secure stateless authentication using Access and Refresh tokens.
- **Refresh Token Rotation (RTR)**: Single-use refresh token rotation to mitigate replay attacks.
- **Role-Based Access Control (RBAC)**: Fine-grained user role guards (`ADMIN`, `LIBRARIAN`, `MEMBER`).
- **Book Inventory Management**: Complete CRUD operations with soft-deletion support.
- **Borrow / Return / Renew**: Seamless loans workflow supporting renewal limits (max 2 renewals) and dynamic fine calculations.
- **FIFO Reservation Queue**: Automated FIFO queue holding system with real-time queue position calculations.
- **Dashboard Analytics**: Dynamic dashboard metrics aggregated directly in SQL database queries.
- **Observability**: Rich telemetry including OpenTelemetry tracing, Prometheus metrics, and Structured JSON logging.

---

## 🏗️ Architecture & Design Patterns

The application follows strict **Clean Architecture** principles and keeps the domain layer completely isolated from transport and persistence concerns:

* **Router Layer (`app/api`)**: Translates HTTP requests and delegates validations to Pydantic schemas.
* **Service Layer (`app/services`)**: Contains pure business logic and transactional boundaries.
* **Repository Layer (`app/repositories`)**: Isolates persistence operations through async data access repository models.
* **Database Layer (`app/models`, `app/db`)**: Manages declarative schemas and connection pools.

### Implemented Design Patterns
* **Repository Pattern**: Abstracting data retrieval and persistence.
* **Dependency Injection**: Injecting database sessions, repositories, and services into routers and services.
* **Service Layer Pattern**: Separating business operations from route handlers.
* **Strategy Pattern**: Dynamic overdue fine calculations (`FlatDailyFineStrategy`).
* **Protocol/Adapter Pattern**: Decoupling reservation holds policies (`ReservationPolicy`).

---

## 📡 API Endpoints & Functional Scope

The platform exposes versioned HTTP REST endpoints (`/api/v1`) enforcing RBAC:

### 🔑 Authentication (`/api/v1/auth`)
* `POST /register` - Register a new account (all roles).
* `POST /login` - Login exchanging credentials for access token & refresh token.
* `POST /refresh` - Rotate refresh token (Single-Use RTR policy).
* `POST /logout` - Invalidate active session and revoke refresh tokens.
* `GET /me` - Retrieve authenticated user profile details.

### 📚 Books Catalog (`/api/v1/books`)
* `GET /` - Search/filter books with pagination (title/author/ISBN/genre).
* `GET /{id}` - Retrieve details of a specific book.
* `POST /` - Register new book (Admin/Librarian).
* `PATCH /{id}` - Update book metadata & inventory levels (Admin/Librarian).
* `DELETE /{id}` - Soft-delete a book (Admin/Librarian).

### 📖 Borrow & Return (`/api/v1/borrow`)
* `POST /` - Checkout book (limits to 5 checkouts, active status checks).
* `POST /{id}/renew` - Renew book due date by 14 days (max 2 renewals).
* `POST /{id}/return` - Return book (idempotent, calculates overdue fine).
* `GET /history` - View own borrowing history with paginated search.

### ⏳ Reservations & Queue holds (`/api/v1/reservations`)
* `POST /` - Reserve an out-of-stock book (FIFO queue positioning).
* `POST /{id}/cancel` - Soft-cancel reservation, immediately promoting the next inline user.
* `GET /active` - List own active reservations with queue positions.
* `POST /sweep` - Sweep expired holds and auto-promote queue (Admin/Librarian).

### 📊 Dashboard & Analytics (`/api/v1/dashboard/summary`)
* `GET /summary` - Calculate metrics (inventory totals, active checkouts, overdue velocity, popular books) over dynamic time windows using database-level SQL aggregations.

---

## 🔒 Security & Hardening

* **Password Hashing**: Stored securely using Argon2/bcrypt hashes.
* **RTR Safety**: Reusing a rotated refresh token immediately revokes the entire token family.
* **Soft Deletes**: Uses logical deletions to prevent referential integrity failures on historical borrow records.
* **SQL Injection Prevention**: Full parameterization using SQLAlchemy's async engine queries.
* **Docker Hardening**: Multi-stage Slim Docker build executing under a non-root system user (`USER appuser`).

---

## 📊 Observability & Metrics

* **Structured Logging**: Contextual structured logging using `structlog`.
* **Trace Propagation**: Auto-instrumented route spans with correlation IDs (`x-request-id`) injected into logs and headers.
* **Prometheus Metrics**: Exposes metrics (`/metrics`) tracking HTTP request latencies, active borrows, active reservations, and queue promotions.
* **Health Checks**: Segmented `/health/live` (process status) and `/health/ready` (active DB connectivity query check) endpoints.

---

## 🧪 Testing

The repository has 68 automated unit, integration, and E2E API tests running against an isolated test environment.

### Run Formatting
```bash
ruff check .
```

### Type Checking
```bash
mypy .
```

### Run Tests & Generate Coverage
```bash
pytest --cov=app --cov-report=term-missing
```

---

## 🚀 Quick Start

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
* **Swagger API Documentation**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health/live`

### Running locally
```bash
# Install dependencies
pip install -e ".[dev]"

# Setup DB configuration in .env and run migrations
alembic upgrade head

# Start local server
$env:MYSQL_SERVER="localhost"; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📁 Documentation

Detailed documentation, design architecture files, and ADRs are stored under the `docs/` directory:
- [00-vision.md](docs/00-vision.md) — Vision and Project Goals.
- [01-functional-requirements.md](docs/01-functional-requirements.md) — Functional Specifications.
- [02-non-functional-requirements.md](docs/02-non-functional-requirements.md) — Performance Targets & Observability.
- [03-architecture.md](docs/03-architecture.md) — ER, Sequence, and FIFO holds diagrams.
- [docs/adr/](docs/adr/) — Architecture Decision Records (0001 to 0015).

---

## 🗺️ Roadmap & Future Improvements

- **Redis Caching Layer**: Cache popular books query counts and metadata.
- **Email Notifications**: Async worker notifications for hold expiration and overdue warnings.
- **Elasticsearch Integration**: Fuzzy search capabilities on catalog titles, authors, and genres.
- **Kubernetes Deployment**: Helm charts for production orchestration.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
