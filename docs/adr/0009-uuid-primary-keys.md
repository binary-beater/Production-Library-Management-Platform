# 0009 - UUID Primary Keys Instead of AUTO_INCREMENT

## Context
Every database entity needs a primary key strategy. The two main options for MySQL are `AUTO_INCREMENT` integers and UUID strings.

## Decision
We use **UUID v4** (`uuid.uuid4()`) stored as `CHAR(36)` for all primary keys.

## Rationale

### Security
- `AUTO_INCREMENT` exposes sequential IDs in API responses: `GET /books/1`, `GET /books/2`.
- An attacker can enumerate all records by incrementing the ID.
- UUIDs (`7d3e4f12-...`) reveal no information about record count, creation order, or business volume.

### Application-Layer Generation
- UUIDs are generated in Python before the INSERT statement executes.
- This means we know the ID before the record exists in the database — useful for correlation, logging, and returning IDs in async workflows.
- `AUTO_INCREMENT` IDs are only known after the database assigns them.

### Distribution Safety
- If the system ever scales to multiple write nodes or shards, UUID PKs guarantee global uniqueness without coordination.
- `AUTO_INCREMENT` requires a central sequence — a distributed bottleneck.

## Trade-offs
- `CHAR(36)` uses more storage than `INT` (36 bytes vs 4 bytes per key).
- UUID indexes have worse locality than sequential integer indexes (random insertion order causes B-tree fragmentation).
- For this project's scale, this trade-off is negligible and the security and architecture benefits dominate.

## Implementation
```python
import uuid
from sqlalchemy import String
from sqlalchemy.orm import mapped_column, Mapped

id: Mapped[uuid.UUID] = mapped_column(
    String(36), primary_key=True, default=uuid.uuid4
)
```
