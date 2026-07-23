# 0006 - Soft Deletes for Catalog & Member Entities

## Context
Physical deletion of primary catalog objects (Books, Members) breaks foreign key referential integrity in historical borrowing audit logs (`borrow_records`).

## Decision
We implement **Soft Deletes** (`is_deleted: bool` and `deleted_at: datetime | None`) for Books and Members.

## Business Rule & Rationale
1. When a Librarian deletes a book, the record is marked `is_deleted = True` and soft-deleted.
2. The soft-deleted book is filtered out from search/list endpoints.
3. Historical borrowing transactions continue to reference the book record without encountering ORM `NULL` / broken foreign key violations.
