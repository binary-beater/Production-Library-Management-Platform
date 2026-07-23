# 01 - Functional Requirements Specification (FRS)

Version: 1.0 (Frozen)

## 1. User Roles & RBAC Matrix

| Feature / Action | Admin | Librarian | Member | Public / Unauthenticated |
|---|---|---|---|---|
| User Registration | ✅ | ✅ | ✅ | ✅ |
| Login / Refresh / Logout | ✅ | ✅ | ✅ | ✅ |
| View Book Catalog & Search | ✅ | ✅ | ✅ | ✅ |
| Create / Update / Delete Book | ✅ | ✅ | ❌ | ❌ |
| Register / Manage Members | ✅ | ✅ | ❌ | ❌ |
| Update Member Status | ✅ | ✅ | ❌ | ❌ |
| Update User Role | ✅ | ❌ | ❌ | ❌ |
| Borrow Book | ✅ | ✅ (for member) | ✅ | ❌ |
| Return Book | ✅ | ✅ | ✅ (own loan) | ❌ |
| Renew Book | ✅ | ✅ | ✅ (own loan) | ❌ |
| View Own Loan History | ✅ | ✅ | ✅ | ❌ |
| View All Active Loans | ✅ | ✅ | ❌ | ❌ |
| View Dashboard & Analytics | ✅ | ✅ | ❌ | ❌ |

## 2. Core Business Rules (BR-001 to BR-011)

- **BR-001**: Email addresses must be unique across all user accounts.
- **BR-002**: Book ISBN must be unique.
- **BR-003**: Passwords are stored only as secure Argon2/bcrypt hashes.
- **BR-004**: Borrow Limit: Maximum 5 active borrowed books per member.
- **BR-005**: Borrow Duration: Default loan period is 14 days.
- **BR-006**: Renewal Limit: Maximum 2 renewals per borrowing record.
- **BR-007**: Available Copies Check: Books with `available_copies == 0` cannot be borrowed.
- **BR-008**: Member Status Check: Inactive members (`membership_status != 'ACTIVE'`) cannot borrow.
- **BR-009**: Soft Deletes: Deleted books and members are marked as `is_deleted = True` with `deleted_at` timestamp. Historical borrow records preserve referential integrity.
- **BR-010**: Immutable Borrow History: Borrow records transition state (`BORROWED`, `RETURNED`, `RENEWED`, `OVERDUE`) and are never physically deleted.
- **BR-011**: Single-Use Refresh Tokens: Refresh tokens are rotated upon use; old tokens are revoked immediately.
