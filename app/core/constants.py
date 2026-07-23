"""
Business Constants — Library Management Platform

These are DOMAIN RULES, not deployment configuration.

Distinction:
  - Environment variables (.env) → secrets, hostnames, credentials (change per deployment)
  - Constants (this file)        → business rules (change only via code review + ADR)

Any change here should be reviewed as a domain decision, not an infra tweak.
"""

# ─── Borrowing Rules ─────────────────────────────────────────────────────────

MAX_BORROW_LIMIT: int = 5
"""Maximum number of books a member may have borrowed simultaneously (BR-004)."""

MAX_RENEWALS: int = 2
"""Maximum number of times a single borrow record may be renewed (BR-006)."""

DEFAULT_LOAN_DAYS: int = 14
"""Default borrow duration in days from the borrow date (BR-005)."""

# ─── Pagination Limits ────────────────────────────────────────────────────────

DEFAULT_PAGE_SIZE: int = 20
"""Default number of items returned per paginated list endpoint."""

MAX_PAGE_SIZE: int = 100
"""Hard ceiling on items per page — prevents unbounded result sets."""

MAX_SEARCH_LIMIT: int = 100
"""Hard ceiling on search result count, regardless of pagination parameters."""
