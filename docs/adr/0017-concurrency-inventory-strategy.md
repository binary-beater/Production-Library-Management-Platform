# 0017 - Concurrency Handling and Inventory Invariant Strategy

## Context
When multiple members attempt to borrow the last available copy of a popular book concurrently, race conditions can occur. Without explicit concurrency controls, the database's `available_copies` count could decrement below zero (resulting in invalid negative inventory) or allow over-allocation of resources.

## Decision
We enforce a strict **Pessimistic Locking** strategy (Pessimistic Write) inside our `BorrowService` transaction boundary when validating and updating book inventory.

### Why Pessimistic Locking over Optimistic Locking?
- **High Contention Behavior**: Under high concurrent contention (e.g. 50 members racing to borrow 1 copy of a newly released best-seller), Optimistic Locking (version columns) would cause high abort rates. Many requests would fail with conflict errors, requiring retry loops and wasting database cycles.
- **Immediate Locking**: Pessimistic Locking (`SELECT FOR UPDATE` in SQL) blocks secondary writes immediately. It forces concurrent requests to wait sequentially in a queue, ensuring that once the lock is acquired, the inventory is guaranteed to be accurate.
- **Fail Fast**: By locking the row at validation time, we prevent subsequent steps from running on stale data.

### Inventory Invariant
The database schema enforces this absolute invariant via Check Constraints:
```sql
0 <= available_copies <= total_copies
```
Pessimistic locking prevents these check constraints from ever being violated, avoiding database transaction aborts.

### Lock Order to Avoid Deadlocks
To prevent deadlocks when locking multiple resources inside a transaction:
1. First, fetch and lock the **Member** record: `SELECT ... FOR UPDATE` on `members`.
2. Second, fetch and lock the **Book** record: `SELECT ... FOR UPDATE` on `books`.

By enforcing a consistent locking order (Member first, then Book) across the application, we guarantee that two concurrent transactions will never block each other in a circular wait state.
