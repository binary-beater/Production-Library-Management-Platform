# Database Query & Index Analysis Plan

## Methodology: EXPLAIN ANALYZE

All slow-path queries will be analyzed using MySQL's `EXPLAIN ANALYZE` before benchmarking.

## Queries To Analyze

### High-Traffic Queries
| Query | Table | Expected Index Used |
|---|---|---|
| Login by email | `users` | `idx_users_email` (UNIQUE) |
| Book search by title | `books` | `idx_books_title` |
| Active loans for member | `borrow_records` | `idx_borrow_member_id` + `idx_borrow_status` |
| Overdue detection | `borrow_records` | `idx_borrow_due_date` (compound) |
| Token lookup on refresh | `refresh_tokens` | `idx_refresh_token_hash` |

## Index Coverage Analysis

After initial implementation, run:
```sql
EXPLAIN ANALYZE
SELECT * FROM borrow_records
WHERE member_id = ? AND status = 'BORROWED';
```

If `type = ALL` (full table scan), add the missing index.

## Findings (To Be Filled After Implementation)

| Query | Rows Examined Without Index | Rows Examined With Index | Improvement |
|---|---|---|---|
| Login lookup | TBD | TBD | TBD |
| Overdue detection | TBD | TBD | TBD |
| Token validation | TBD | TBD | TBD |
