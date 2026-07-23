# Resume Claims Validation Matrix

| Resume Claim / Metric | Target Value | Verification Evidence Source |
|---|---|---|
| 26 REST APIs | 26 endpoints | `docs/05-api-spec.md` + FastAPI routes in `app/api/v1/` |
| Automated Test Suite | 190+ tests | PyTest test discovery (`tests/unit`, `tests/integration`, `tests/api`) |
| Code Coverage | >= 90% | `pytest --cov=app` XML report & GitHub Actions summary |
| Recorded API Interactions | 140 interactions | Keploy test files & session recordings |
| Regression Scenarios | 68 scenarios | Keploy automated test suite |
| Multi-Stage CI/CD | 4-Stage GitHub Pipeline | `.github/workflows/ci.yml` |
| Layered Architecture & RBAC | Clean Architecture | `app/services/`, `app/repositories/`, `app/security/` |
