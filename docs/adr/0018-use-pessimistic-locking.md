# 0018 - Pessimistic Locking Strategy for Concurrency Control

## Context
In a multi-user library management platform, concurrent requests to borrow the same book (with limited copies) or modify a member's standing can cause race conditions. If two users check out the last copy of a book at the same millisecond, both requests might pass validation before the database is updated, leading to negative inventory (`available_copies < 0`).

## Decision
We implement **Pessimistic Locking** (`SELECT ... FOR UPDATE`) to manage concurrency on high-contention rows.

### Why Pessimistic over Optimistic Locking?
1. **High Contention Abort Avoidance**: Optimistic locking (version checks) forces transaction rollbacks when conflicts are detected. Under high concurrent pressure (e.g. 50 members racing to borrow 1 popular copy), Optimistic locking results in high transaction failure rates and retry loops. Pessimistic locking handles this by placing users in a sequential database-level queue, improving success rates under high contention.
2. **Lock Order to Prevent Deadlocks**: To prevent circular wait states (deadlocks), transactions will consistently acquire locks in this order:
   - First: Lock the **Member** row.
   - Second: Lock the **Book** row.
3. **Database Constraints Integrity**: Databases act as our final defense line. Pessimistic locking prevents transactions from violating constraints like:
   - `available_copies >= 0`
   - `available_copies <= total_copies`

## Alternatives Considered
- **Optimistic Concurrency Control (OCC)**: Rejected due to transaction abort overhead under high contention.
- **Queueing (Redis/RabbitMQ)**: Good for high scale but introduces system complexity (distributed lock syncs). Pessimistic DB locks are self-contained and sufficient for our scale targets.
