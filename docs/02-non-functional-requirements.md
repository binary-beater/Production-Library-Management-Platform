# 02 - Non-Functional Requirements Specification (NFR)

Version: 1.0 (Frozen)

## 1. Performance Target Metrics
- **Simple GET Endpoints**: < 100 ms
- **Auth Endpoints (Login/Register)**: < 200 ms
- **Multi-Criteria Search**: < 300 ms
- **Borrow / Return Workflows**: < 300 ms
- **Dashboard Analytics**: < 500 ms
- **Throughput Target**: 100 requests/sec with 50 concurrent users under load testing.

## 2. Security Standards
- **Password Security**: Argon2 / Bcrypt password hashing with high work factor.
- **Tokens**: Short-lived JWT Access Tokens (15 mins), Long-lived Refresh Tokens (7 days) with rotation & revocation table.
- **Input Validation**: Pydantic v2 schemas for all incoming HTTP payloads.
- **Authorization**: Endpoint-level RBAC guards via FastAPI dependencies.

## 3. Testing & Quality Requirements
- **Coverage**: Target >= 90% overall line and branch coverage.
- **Test Count**: 190+ automated tests (Unit, Integration, E2E API).
- **Regression**: Keploy recorded API test interactions and regression runs.

## 4. Observability & Maintainability
- **Structured Logging**: JSON logging with Correlation ID (`x-request-id`) injected into context.
- **Metrics**: Prometheus `/metrics` endpoint measuring RPS, request duration histogram, HTTP status codes.
- **Tracing**: OpenTelemetry auto-instrumentation for FastAPI request lifecycles.
