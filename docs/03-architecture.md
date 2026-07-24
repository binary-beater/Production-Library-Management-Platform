# 03 - System Architecture Document

Version: 1.0

## 1. High-Level Architectural Layers

```text
               Client (HTTP / REST)
                        │
                FastAPI API Layer (`app/api/v1`)
                        │
             Dependencies & Security (`app/dependencies`, `app/security`)
                        │
              Business Logic Service (`app/services`)
                        │
               Repository Layer (`app/repositories`)
                        │
            ORM & Database (`app/models`, `app/db`) -> MySQL 8.0
```

## 2. Directory Layout & Layer Responsibilities

- **`app/api/`**: HTTP endpoints, input/output serialization using Pydantic, HTTP status code management. No business logic or DB calls.
- **`app/services/`**: Core domain logic, validation of business rules, workflow orchestration, atomic transaction management.
- **`app/repositories/`**: Database queries, CRUD abstraction, filters, pagination, SQLAlchemy ORM interactions.
- **`app/models/`**: Declarative SQLAlchemy models.
- **`app/schemas/`**: Strict Pydantic v2 validation models.
- **`app/core/`**: Configuration, security utilities, and structured logging.
- **`app/middleware/`**: Cross-cutting HTTP middlewares (Correlation ID, Process Time, Exception Handler).

---

## 3. Visual System Diagrams

### 3.1 Entity-Relationship (ER) Diagram
This diagram outlines the complete database schema layout, showing relationship bounds across users, members, book metadata, borrowing transactions, and FIFO queue reservations.

```mermaid
erDiagram
    User ||--o| Member : "profile_owner"
    Member ||--o{ BorrowRecord : "borrow_history"
    Member ||--o{ Reservation : "reservation_queue"
    Book ||--o{ BorrowRecord : "loan_history"
    Book ||--o{ Reservation : "waiting_list"

    User {
        uuid id PK
        string email UK
        string password_hash
        string role "ADMIN | LIBRARIAN | MEMBER"
        boolean is_active
        datetime created_at
    }

    Member {
        uuid id PK
        uuid user_id FK
        string membership_number UK
        date joined_date
        string membership_status "ACTIVE | SUSPENDED"
        boolean is_deleted
        datetime deleted_at
    }

    Book {
        uuid id PK
        string title
        string author
        string isbn UK
        integer total_copies
        integer available_copies
        boolean is_deleted
        datetime deleted_at
    }

    BorrowRecord {
        uuid id PK
        uuid member_id FK
        uuid book_id FK
        datetime borrow_date
        datetime due_date
        datetime return_date
        string status "BORROWED | RETURNED | RENEWED | OVERDUE"
        integer renewal_count
    }

    Reservation {
        uuid id PK
        uuid member_id FK
        uuid book_id FK
        datetime reserved_at
        datetime expires_at
        string status "PENDING | HOLD | COMPLETED | CANCELLED | EXPIRED"
    }
```

### 3.2 Request Correlation & Middleware Lifecycle
This sequence diagram tracks the flow of an HTTP request, demonstrating correlation header injection via context-local variables (`contextvars`), Prometheus metrics logging, and OpenTelemetry spans tracing.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Middleware as HTTP Middleware
    participant Controller as API Controller
    participant Service as Business Service
    participant Database as MySQL Database

    Client->>Middleware: Send HTTP Request (e.g. GET /api/v1/dashboard/summary)
    Note over Middleware: Extract or generate correlation ID (x-request-id)
    Note over Middleware: Bind correlation ID to contextvars
    Note over Middleware: Start OpenTelemetry transaction span

    Middleware->>Controller: Route Request to Controller
    Controller->>Service: Delegate Business Logic
    Service->>Database: Query aggregated metrics (SELECT ...)
    Database-->>Service: Return aggregated results
    Service-->>Controller: Return response payload
    Controller-->>Middleware: Return HTTP Response

    Note over Middleware: Stop timing duration (elapsed seconds)
    Note over Middleware: Emit structured structlog JSON log with correlation ID
    Note over Middleware: Record Prometheus metrics (http_requests_total)

    Middleware-->>Client: HTTP Response + Header (x-request-id)
```

### 3.3 FIFO Reservation Expiration & Promotion Flow
This sequence diagram shows the automatic promotion workflow triggered during hold queue cancellations or background sweeper runs.

```mermaid
sequenceDiagram
    autonumber
    actor Member
    participant Service as ReservationService
    participant Repo as ReservationRepository
    participant DB as MySQL Database

    Member->>Service: Cancel Reservation (HOLD status)
    Note over Service: Initiate Transaction Block
    Service->>Repo: Get reservation record for update (FOR UPDATE lock)
    Repo->>DB: Fetch record
    DB-->>Repo: Lock & return record
    Service->>Repo: Update cancelled reservation status to CANCELLED

    Note over Service: Trigger Promotion Chain
    Service->>Repo: Fetch oldest PENDING reservation for Book (FIFO)
    Repo->>DB: SELECT * FROM reservations WHERE status='PENDING' ORDER BY reserved_at ASC LIMIT 1
    DB-->>Repo: Return oldest pending record (or None)

    alt Next Reservation Exists
        Service->>Repo: Transition status to HOLD & set expires_at (48h duration)
        Repo->>DB: Save updated next reservation
        Note over Service: Increment reservation_promotions_total metric
    else No Reservations Pending
        Service->>Repo: Fetch Book for update
        Service->>DB: Increment book.available_copies by 1
    end

    Note over Service: Commit Transaction Block
    Service-->>Member: Return Cancelled Confirmation
```
