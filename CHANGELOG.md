# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-07-26

### Added
- **Authentication**: Added JWT sign-in, signup, refresh token rotation (RTR), and logout endpoints.
- **Books Catalog**: Complete CRUD with pagination, metadata validation, and soft-delete capabilities.
- **Borrow & Return**: Book checkouts with a max limit of 5, renew options (max 2), and idempotent return handlers with dynamic fine computations.
- **Reservations & FIFO Hold Queue**: Automated book reservations for out-of-stock titles; holds automatically promote the next member in the FIFO queue on cancels or returns.
- **Dashboard Analytics**: Exposes structured SQL aggregations over dynamic time windows (popular books, borrow counts, active velocity).
- **Observability**: Exposes Prometheus metrics, Structured JSON logging, OpenTelemetry context tracing, and ready/live health checkpoints.
