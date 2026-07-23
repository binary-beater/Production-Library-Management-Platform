# 0012 - Structlog for Structured JSON Logging

## Context
Python's built-in `logging` module outputs unstructured plain text logs. In production systems, logs need to be machine-parseable by aggregators (Datadog, ELK, Loki, CloudWatch) and carry contextual fields like `request_id`, `user_id`, `method`, and `latency`.

## Decision
We use **structlog** with `JSONRenderer` to emit structured JSON log lines to stdout.

## Why Structlog Over Standard `logging`?
| Standard `logging` | structlog |
|---|---|
| Plain text output | Structured JSON output |
| Hard to add contextual fields | `structlog.contextvars` merges request context automatically |
| No processor pipeline | Chainable processor pipeline (add timestamps, log levels, stack traces) |
| Requires formatters to parse in aggregators | Natively parseable by any JSON log aggregator |

## Log Format
Every log line emits:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "event": "Borrow book request",
  "request_id": "7d3e4f12-...",
  "user_id": "b8f2a1c3-...",
  "book_id": "a9e4b2d1-...",
  "method": "POST",
  "path": "/api/v1/borrows"
}
```

## Correlation ID Integration
The `structlog.contextvars.merge_contextvars` processor merges request-scoped variables (set by our Correlation ID middleware) into every log line emitted during that request — without passing them manually through every function call.
