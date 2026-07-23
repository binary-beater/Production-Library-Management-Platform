# 0011 - Alembic for Database Schema Migrations

## Context
Database schemas evolve as features are added. We need a way to version, apply, and roll back schema changes reproducibly across every environment (local, CI, staging, production).

## Decision
We use **Alembic** as our database migration tool, configured with SQLAlchemy's `MetaData` to auto-generate migrations from model changes.

## Why Not `Base.metadata.create_all()`?
| `create_all()` | Alembic |
|---|---|
| Creates tables from scratch only | Generates incremental migration scripts |
| Cannot alter existing columns | Supports `ALTER TABLE`, adding/removing columns |
| No history — can't roll back | Full version history with `upgrade` and `downgrade` |
| Not usable in production | Standard production migration practice |

## Migration Naming Strategy
All migration files use a descriptive prefix:
```
migrations/versions/
    0001_initial_schema.py
    0002_add_indexes.py
    0003_add_refresh_tokens.py
```
Generated with: `alembic revision --autogenerate -m "initial_schema"`

## Configuration
- `alembic.ini` uses `SYNC_DATABASE_URI` (pymysql) — Alembic does not support async drivers.
- `env.py` imports `Base.metadata` so autogenerate detects all model changes.
- Migrations run on application startup in development; manually reviewed and applied in production.
