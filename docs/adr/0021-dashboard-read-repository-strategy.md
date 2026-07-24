# 0021 - Isolated Read-Only Dashboard Repository Strategy

## Context
Exposing operations analytics (e.g. borrowing velocity, top-5 checkout volumes, active hold states) requires executing SQL aggregate queries (e.g. `SUM`, `COUNT`, `AVG`, `GROUP BY`).
If these queries are executed within the core transactional repositories (like `BookRepository` or `BorrowRecordRepository`), we risk polluting transactional domains with read-only reporting structures.
Additionally, running analytical operations on transactional sessions under high concurrency can create database lock contention.

## Decision
We implement a dedicated, read-only data access abstraction layer: **`DashboardRepository`**.

### Specifications:
1. **Separation of Concerns**: `DashboardRepository` will strictly house reporting and analytical queries. Transactional repositories remain lightweight and focused on row-level mutations.
2. **Aggregations in SQL**: All analytical computations (e.g., sums of available copies, overdue ratios, top book borrow counts) will occur at the database level via SQL aggregations. No raw rows will be loaded into Python memory for client-side processing.
3. **No Lock Queries**: Queries in this repository will run without locking modifiers (no `with_for_update()`) to prevent holding locks that block checkout/return threads.
