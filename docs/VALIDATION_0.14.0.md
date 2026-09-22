# Local release validation — v0.14.0

Validated on 2026-09-22 on macOS with host Python 3.11, Docker Engine 29.6.2, and the Python 3.12 slim container image.

| Check | Observed result |
|---|---|
| Full unittest suite | 119 tests passed (106 existing + 13 delegation tests) |
| Docker Compose build and health startup | Both services healthy |
| Original ticket evaluator | 17/17 passed before and after service restart |
| Delegation evaluator | 19/19 passed before and after service restart |
| Primary and child isolation probes | Operator API denied; backend unreachable by service name and direct IP for each role |
| Pre-restart delegation lineage | Stored nodes and actions identical after restart |
| Built wheel in clean virtual environment | Version 0.14.0; both evaluators passed (17/17 and 19/19) |
| Secret initialization/upgrade | Fresh init and init-child passed; existing keys preserved, overwrite refused |
| Gateway container runtime | UID/GID 10001; effective capabilities zero |
| Evidence export | Export succeeded; event chain verified by evaluations |

The new regression tests cover scope and lifetime narrowing, identity misuse, parent pause/resume/revocation, parent and child expiry, exact approval for delegated updates, persistent lineage, and atomic rollback when delegation evidence cannot be committed.

Reproduce using [the reviewer guide](REVIEW_GUIDE.md). Example evaluation output is in [ticket evaluation](pilot-evaluation-example.json) and [delegation evaluation](delegation-evaluation-example.json). These are synthetic local runs by the developer's assistant, not independent reviewer findings or endorsements. Timing values are observations, not performance benchmarks.

Python 3.10/3.13 and hosted GitHub Actions were not run locally. No live model, third-party ticket platform, MCP integration, enterprise identity provider, production deployment, or external penetration test was validated. Docker isolation results apply to the supplied network topology and role containers. Service restarts do not establish host-failure recovery, backups, or distributed consistency.
