# v0.13.0 pilot validation

Validated locally on macOS with Python 3.11 and Docker Desktop Engine 29.6.2, using Python 3.12-slim in the containers.

| Check | Observed result |
|---|---|
| Full unittest suite | 106 passed, including 16 new pilot tests |
| Local REST workflow | 17/17 evaluation checks passed |
| Compose build and health readiness | Both services built, started, and healthy |
| Containerized REST workflow | 17/17 checks passed |
| Restart with persistent volumes | Services healthy; 17/17 checks passed again |
| Agent-only operator request | Denied |
| Agent-to-backend network test | Service-name and direct-IP connections both blocked |
| Runtime privilege inspection | Application UID/GID 10001; effective capabilities zero |
| Wheel/source build | Completed |
| Fresh wheel installation | Installed package and both CLI entry points verified |

Security regressions include canonical approval substitution, wrong-role access, nonce replay, unauthenticated direct tool access, concurrent approved requests, transactional backend idempotency, stale versions, approval expiry, missing/mismatched receipts, simulated response loss after mutation, gateway restart, pause/revocation, arbitrary resource URLs, and redirect rejection.

The sanitized `pilot-evaluation-example.json` was produced by the actual Docker deployment using synthetic data. Latency samples include tool I/O and are not benchmark claims. Request counts include retries and approval holds.

Not performed: external organizational deployment, real ticketing-provider integration, live-model evaluation, corporate IdP integration, hosted GitHub Actions, penetration test, multi-host TLS deployment, or production load testing. Local testing does not establish effectiveness against all attacks.

The evaluation programmatically uses both roles. Human review instructions are provided separately in TICKET_PILOT.md. No external reviews or endorsements are implied.
