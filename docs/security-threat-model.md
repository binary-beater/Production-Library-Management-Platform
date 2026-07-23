# Security Threat Model & Mitigations

This document outlines the identified security risks for the Library Management Platform and their corresponding mitigations.

| Threat / Attack Vector | Risk | Mitigation Strategy |
|---|---|---|
| **Database Compromise (Password Leak)** | High | Passwords hashed using **Argon2id** (64MB, 3 iterations, 4 threads). Even under raw DB leaks, GPU-based dictionary/brute-force attacks are economically unfeasible. |
| **Refresh Token Theft** | High | **Refresh Token Rotation (RTR)**. Every time a refresh token is used, it is invalidated and replaced. |
| **Token Replay / Hijacking** | High | **Token Family Tracking**. Refresh tokens are linked by a `family_id` UUIDv4. If a revoked token is reused (indicating theft), the entire family lineage is instantly revoked. |
| **JWT Signature Forgery** | High | Cryptographically signed using **HS256** with a high-entropy secret. Key rotation to asymmetric key pairs (`RS256` / JWKS) planned. |
| **SQL Injection (SQLi)** | Medium | Implemented using **SQLAlchemy 2.0 ORM** and expression-based parameter binding. Raw queries are avoided. |
| **Timing Attacks** | Medium | Constant-time password verification via `passlib` context comparator prevents timing attacks on password verification. |
| **Man-in-the-Middle (MITM)** | High | **HTTPS** enforced (TLS 1.3). HSTS headers (`Strict-Transport-Security`) enforce TLS transport. |
| **Cross-Site Scripting (XSS)** | High | Access tokens are kept in memory only. Refresh tokens are returned in responses but designed to be stored in **`HttpOnly`**, **`Secure`**, **`SameSite=Strict`** cookies in production. |
| **Cross-Site Request Forgery (CSRF)** | Medium | Not applicable. Access tokens are passed via headers (`Authorization: Bearer <token>`). Browsers do not auto-attach authorization headers on cross-site requests. |
| **Brute-Force Login Attacks** | Medium | **Login Rate Limiting**. Account and IP-based lockout limits consecutive failures (planned). |
| **Clock Skew Mismatches** | Low | JWT validation permits a **60-second** clock skew margin to account for server time drift. |
