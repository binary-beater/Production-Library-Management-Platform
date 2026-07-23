# 0005 - Single-Use Refresh Token Rotation

## Context
Standard JWT authentication issue: Long-lived refresh tokens, if stolen, allow attackers persistent unauthorized access until expiration.

## Decision
We implement **Single-Use Refresh Token Rotation** with a server-side revocation table (`refresh_tokens` table in MySQL).

## Rationale & Mechanism
1. Whenever a client calls `POST /api/v1/auth/refresh` using a refresh token:
   - The server verifies token signature & checks `revoked == False` in DB.
   - The current refresh token is immediately marked `revoked = True`.
   - A brand new Access Token AND a brand new Refresh Token are generated and returned.
2. If a revoked refresh token is presented again, it triggers security alarm logic (revoking all active tokens for that user session).

## Security Benefits
- Prevents token replay attacks.
- Limits exposure window of compromised refresh tokens.
