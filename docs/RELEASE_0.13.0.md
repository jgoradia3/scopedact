# v0.13.0 — Isolated support-ticket pilot

ScopedAct now includes a concrete REST-backed workflow that an independent reviewer can run with synthetic data: read an assigned ticket, propose an update, review and approve exact content as a separate operator, execute once, intervene, and export evidence.

## New components

- Contextual connector contract preserving request/task identity and reviewed input.
- Fixed-route REST ticket connector with response limits, timeout, no inherited proxies, and no redirects.
- Persistent synthetic backend with atomic idempotency receipts and expected-version checks.
- Separate signed agent and operator API roles, authenticated CLI review/approval, and five-minute approval expiry.
- Read-only reconciliation of uncertain update results using backend receipts.
- Redacted evidence export and a deterministic 17-check evaluation harness.
- Compose deployment with private backend network, no backend host port, file-based secrets, read-only container filesystems, and non-root application processes.
- Agent-only network probe testing both service-name and direct-IP access.

## What this enables

Invite a reviewer to run a controlled synthetic pilot, challenge the controls, inspect the records, and suggest integration requirements. The pilot makes real HTTP calls and persists real synthetic updates. It does not yet connect to Jira, ServiceNow, AWS, MCP, or an organization's identity provider.

The older local workspace remains available. The pilot's authenticated CLI does not change the authentication status of the old operator console.

## Validation

See PILOT_VALIDATION.md. No independent evaluation, organizational adoption, or production certification is claimed.
