# Repository Coding & Layering Standards

## 1. Directory Structure Standards
```text
app/
├── api/v1/         # FastAPI Route Handlers
├── core/           # System Configurations, Security, Logging
├── db/             # SQLAlchemy Engine & Base
├── dependencies/   # FastAPI Dependencies (Auth, Service Providers)
├── exceptions/     # Custom Exception classes & Handlers
├── middleware/     # Custom Middlewares
├── models/         # SQLAlchemy ORM Models
├── repositories/   # Database Data Access Repositories
├── schemas/        # Pydantic v2 Request/Response Schemas
├── services/       # Core Business Logic Services
└── utils/          # Pagination & General Helpers
```

## 2. Naming Conventions
- **Schemas**: `[Entity][Action]Request` / `[Entity]Response` (e.g., `BookCreateRequest`, `BookResponse`)
- **Services**: `[Entity]Service` (e.g., `BorrowService`)
- **Repositories**: `[Entity]Repository` (e.g., `BookRepository`)
- **Exceptions**: `[Domain]Exception` (e.g., `BookNotAvailableException`)

## 3. Layering Rules
1. API Routers MUST NOT call Repositories or DB sessions directly; they MUST invoke Services.
2. Services contain ALL business rule validation and domain logic.
3. Repositories handle database querying, filtering, and pagination.
4. Models define ORM entities and relationships.
