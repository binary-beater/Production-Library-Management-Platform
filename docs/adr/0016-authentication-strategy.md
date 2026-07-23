# 0016 - Token-Based Authentication Strategy with RTR and Argon2id

## Context
We need to authenticate users, manage sessions, and secure resource endpoints. Unsecured sessions lead to account takeover, token leakage, or performance bottlenecks.

## Decision
We implement a hybrid token authentication architecture:
1. **Stateless Access Tokens**: JWT (`HS256`, 15-minute expiry) containing claims: `sub`, `role`, `jti`, `iat`, `nbf`, `exp`, `iss`, `aud`.
2. **Stateful Refresh Tokens**: Hex-encoded SHA-256 fingerprints of raw cryptographically secure tokens (`secrets.token_urlsafe(64)`), rotated on every request (Refresh Token Rotation - RTR) and grouped by a `family_id` UUIDv4.
3. **Password Hashing**: **Argon2id** (configured via `passlib[argon2]`).

## Why this Architecture?
- **Stateless Verification**: High-frequency APIs verify access tokens entirely in memory, eliminating database overhead.
- **Argon2id vs Bcrypt**: Argon2id is memory-hard and time-hard, providing maximum defense against GPU-accelerated brute-forcing.
- **RTR & Family Tracking**: Prevents replay attacks. If a refresh token is leaked, reusing it invalidates the entire `family_id` lineage immediately, locking out both the attacker and the victim.
- **Token Fingerprints**: We never store raw tokens in MySQL. A compromise of the `refresh_tokens` table only exposes SHA-256 fingerprints, rendering them useless for authentication.
- **No Redis Blacklist**: Short-lived (15m) access tokens expire naturally, eliminating the need for a low-latency blacklist cache.

## Token Family Lifecycle State Machine
```
   [REGISTERED]
        │
        ▼
     [LOGIN]  ─── (Creates Family ID, Access JWT & Refresh Token Fingerprint)
        │
        ▼
     [ACTIVE]
        │
        ├──────► [REFRESH] (RTR: Revokes old Token, Issues New Token in same Family)
        │           │
        │           └─► (Detected Reuse?) ──► [REVOKE FAMILY] (Purges lineage)
        ▼
    [LOGOUT]  ─── (Marks current Refresh Token as Revoked)
```

## Refresh Token Exchange Flow
```
Client                      AuthService               DB
  │                             │                      │
  ├─ POST /auth/refresh ───────►┤                      │
  │  (raw refresh token)        ├─ get_by_fingerprint ─►┤ (SELECT)
  │                             │  SHA-256(token)      │
  │                             ◄──────────────────────┤ (Token Record)
  │                             │                      │
  │                             ├─ Check Expired?      │
  │                             ├─ Check Revoked?      │
  │                             │                      │
  │                             ├─ Yes (Breach!) ──────► (Revoke entire family_id)
  │                             │                      │
  │                             └─ No (Clean RTR) ─────► (Mark old revoked, create new)
  ◄─ HTTP 200 (New tokens) ─────┤                      │
```

## JWT Claims Verification Flow
```
Verify Signature ──► Verify Expiry (with Skew) ──► Verify Not Before ──► Verify Audience ──► Verify Issuer ──► Accept
```
Clock skew allowance is set to **60 seconds** to tolerate time differences between clients and servers.
