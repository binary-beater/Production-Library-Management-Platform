# Performance Load Testing Plan

## Tool: Locust

All load tests are written using **Locust** (`locust>=2.24.0`) and live in `benchmarks/`.

## Test Scenarios

### Scenario 1: Baseline API Throughput
- **Target**: 100 RPS sustained with 50 concurrent users
- **Endpoints**: Health check, Book list, Book search
- **Duration**: 3 minutes steady state

### Scenario 2: Auth Throughput
- **Target**: Login + Refresh token exchange under 200ms at P95
- **Concurrent users**: 20

### Scenario 3: Borrow Workflow Load
- **Target**: Borrow + Return cycle under 300ms at P95
- **Concurrent users**: 30
- **Validates**: Atomic transaction integrity under concurrent load

### Scenario 4: Search Performance
- **Target**: Multi-criteria search under 300ms at P95
- **Variants**: Title search, author search, ISBN lookup, genre filter

## Metrics Captured Per Test
| Metric | Target |
|---|---|
| P50 latency | < 50ms for GET |
| P95 latency | < defined target per endpoint |
| P99 latency | < 3x P95 |
| Error rate | < 0.1% at target load |
| RPS sustained | 100+ |

## Evidence For Resume
Results are stored in `metrics/latency.md` and `metrics/benchmark.md`.
Every resume claim maps to a recorded test run.
