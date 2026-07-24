# 0019 - Reservation Queue and Hold Strategy

## Context
When all copies of a popular book are checked out, members must wait until one is returned. Rather than requiring users to manually check back repeatedly (causing high query volume and poor user experience), we need a fair queueing mechanism to allocate books to waiting users.

## Decision
We implement a **FIFO (First-In, First-Out) Reservation & Hold Queue** system.

### How it works:
1. **Reservation State**: When a member requests a book that is currently out of stock (`available_copies == 0`), they can place a **Reservation**. This places them in a queue for that book.
2. **Hold State**: When a copy of the book is returned:
   - The system checks if there are any active reservations.
   - If a reservation exists, the book's `available_copies` remains at `0` (it is not put back on the general shelf).
   - The top reservation transitions to a **Hold** state (held for the user).
   - A **48-hour expiration window** starts.
   - If the member borrows the book within 48 hours, the hold transitions to `COMPLETED` and a `BorrowRecord` is created.
   - If the 48-hour window expires without checkout, the reservation transitions to `EXPIRED`, and the book is automatically offered to the next reservation in line (or returned to general inventory if the queue is empty).

### Concurrency Lock Order
To avoid deadlocks when processing reservations and checkouts concurrently:
1. Lock **Book** row first (`SELECT FOR UPDATE`).
2. Lock **Reservation** row next (`SELECT FOR UPDATE`).
3. Lock **Member** row last (`SELECT FOR UPDATE`).

This consistent ordering ensures absolute consistency on queue positions and inventory invariants.
