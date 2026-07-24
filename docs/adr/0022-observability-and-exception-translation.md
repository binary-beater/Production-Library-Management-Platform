# ADR-0022: Production Observability, Metrics, Tracing, and Exception Translation

## Context
Production-grade backends must expose clear indicators of their internal states (metrics, traces, logs) and prevent leaking internal implementation specifics (raw database stack traces) to external clients during failures. We need a unified strategy mapping request correlation headers across logging contexts, exporting operational metrics, exporting traces, and translating internal domain errors into standardized error envelopes.

## Decision
1. **Request Correlation**: Employed a custom HTTP middleware extracting or generating `x-request-id` headers. This value is registered in `contextvars` context-local storage.
2. **Structured Logging**: Configured `structlog` JSON renderer. The correlation ID context variable is merged into all logger dictionaries, ensuring every log emitted during a request automatically includes it.
3. **Prometheus Metrics**: Defined domain and HTTP metrics inside an isolated `app.core.metrics` module to prevent circular dependency import errors. Registered `/metrics` endpoint.
4. **OpenTelemetry Tracing**: Integrated `FastAPIInstrumentor` to trace HTTP transactions.
5. **Distinct Liveness & Readiness checks**:
   - `/health/live`: Statically verifies FastAPI process uptime.
   - `/health/ready`: Performs active query executions on `session` to confirm database connectivity.
6. **Exception Translation**: Registered central FastAPI exception handlers mapping `ApplicationException` (and validation errors) to standard structured responses.

## Consequences
- Better operational visibility, correlation, and metric aggregation.
- Eliminates circular import risks by isolating metrics.
- Increased runtime security (zero raw database trace leaks).
