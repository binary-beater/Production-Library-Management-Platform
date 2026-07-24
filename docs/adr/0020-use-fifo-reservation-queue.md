# 0020 - FIFO Reservation Queue Allocation Strategy

## Context
When a book has 0 available copies in inventory, members can place reservations. When copies are returned, we must decide how to prioritize which reservation gets promoted to a hold state.

## Decision
We implement a strictly time-ordered **First-In, First-Out (FIFO)** reservation queue strategy based on the creation timestamp (`reserved_at`).

### Why FIFO?
1. **Equity and Fairness**: Library materials are public resources. A FIFO queue guarantees that wait time is directly proportional to when the request was placed, avoiding starvation.
2. **Implementation Simplicity**: FIFO can be index-optimized using simple DB compound index strategies:
   ```sql
   CREATE INDEX idx_reservations_fifo ON reservations (book_id, status, reserved_at);
   ```
   This index matches our promotion query directly, making queue lookups $O(1)$ operations:
   ```sql
   SELECT * FROM reservations
   WHERE book_id = :book_id AND status = 'PENDING'
   ORDER BY reserved_at ASC
   LIMIT 1;
   ```

### Alternatives Considered
- **Priority-Based Queues (e.g., Faculty > Student > Guest)**: Rejected for the initial version to prevent priority inversion where student reservations are perpetually starved by incoming faculty requests.
- **Dynamic Queue Positions**: Storing queue positions (e.g. `queue_position = 1, 2, 3`) in a database column. Rejected because cancellations or expirations require updates to all subsequent rows (causing high write volumes and locks). We compute positions dynamically instead:
  ```sql
  SELECT COUNT(*) FROM reservations
  WHERE book_id = :book_id AND status = 'PENDING' AND reserved_at < :my_reserved_at;
  ```
  This is a clean, read-only calculation that avoids write contention.
