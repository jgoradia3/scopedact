# Managed workspace validation — 0.15.0

Local validation on October 2, 2026. These are maintainer-run checks, not independent adoption evidence.

- Full Python 3.11 suite: 132 tests passed. SQLite ownership checker: 1,558 connections opened, zero unclosed.
- Source distribution and wheel built successfully, including workspace web assets.
- Docker Compose gateway built, became healthy, and accepted signed requests through the loopback port.
- Both agent container probes passed: operator routes denied; no document database, operator key, or Docker socket accessible.
- Scripted HTTP workload: 104 attempts, including 101 helper reads, one blocked out-of-scope read, and one held update.
- Browser operator login, activity map, exact before/after proposal review, approval, and pause controls exercised. After browser approval, the agent retry executed and produced document version 2.
- Gateway recreation retained assignments and document history.

Counters describe historical attempts: a held attempt remains in history after a later successful retry. Current proposal status appears separately below the map.

The demo uses scripted clients and development HMAC roles. It covers only actions routed through the managed-workspace gateway. Imported documents are copies, not live host files. See [the workspace guide](WORKSPACE.md) for setup and limitations.

A managed-workspace GitHub Actions job is included, but its hosted result is unverified until this source is published. Browser checks are manual; there is no automated browser regression suite.
