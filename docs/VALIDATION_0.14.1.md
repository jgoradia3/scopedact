# Local release validation — v0.14.1

Validated on 2026-09-22. This is local engineering validation, not independent review or hosted GitHub CI.

| Check | Result |
|---|---|
| Full suite, host Python 3.11 | 120 tests passed |
| Full suite, Linux Python 3.13 container | 120 tests passed; no ResourceWarnings |
| Explicit SQLite ownership check, both environments | 857 connections opened; zero unclosed |
| Child approval followed by parent pause/revoke | Denied without ticket changes or mutation receipt |
| Docker Compose build/startup | Both services healthy; Docker Engine 29.6.2, Python 3.12 service image |
| Ticket evaluator | 17/17 before and after restart |
| Delegation evaluator | 19/19 before and after restart |
| Primary and child isolation probes | Operator API denied; backend unreachable by service name and direct IP |
| Package build and fresh virtual environment | Source/wheel built; installed CLI reports 0.14.1 and passes 17/17 plus 19/19 checks |
| Internal documentation links | No missing relative targets |
| Pre-restart lineage | Identical stored nodes and actions after restart |

The ownership checker retains and inspects in-process SQLite connections after the test suite, including request-handler threads. This makes connection leaks fail CI on Python versions predating SQLite ResourceWarnings. It is not a general memory/resource profiler and does not inspect connections inside separate subprocesses.

Reproduce using [the reviewer guide](REVIEW_GUIDE.md). The source includes normalized synthetic [ticket](pilot-evaluation-example.json) and [delegation](delegation-evaluation-example.json) examples; generated runtime directories, keys, and databases are excluded from the review ZIP.

Python 3.10 and hosted GitHub Actions were not run here. The test configuration covers Python 3.10–3.13, but configuration alone is not a hosted success claim. No live model, MCP, enterprise identity provider, real ticket platform, production deployment, independent penetration test, or external adoption was validated. Restart checks do not establish backups or distributed consistency.
