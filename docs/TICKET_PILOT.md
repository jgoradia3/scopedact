# ScopedAct support-ticket pilot — v0.14.1

A complete, provider-neutral **synthetic test workflow**: an agent reads its assigned ticket, proposes a comment, and an authenticated operator reviews and approves the exact change before the REST tool executes it. No cloud account, paid model, or production credentials are needed.

This is suitable for independent local evaluation. It is not a Jira/ServiceNow integration, enterprise identity system, or production deployment.

For parent/child delegation, continue with [DELEGATION.md](DELEGATION.md).

## Start with Docker Compose

Requirements: Python 3.10+, Docker Desktop/Engine with Compose. Run these commands from the extracted repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
scopedact-pilot init
docker compose -f compose.pilot.yaml up --build -d --wait
```

`init` creates four independent secrets (primary agent, child agent, operator, and tool) under `.scopedact-pilot/secrets/`, refuses to overwrite them, and does not print them. Keep this directory private and out of Git. The supplied gitignore and dockerignore exclude it. If upgrading from v0.13, run `scopedact-pilot init-child`; if all four keys already exist, skip initialization.

Services:

| Component | Reachability | Credentials |
|---|---|---|
| Gateway | Host loopback port 8870; agent network | Verifies separate signed primary/child/operator requests |
| Ticket REST service | Private Docker network only; no host port | Tool key, held by gateway and ticket service |
| Agent probe | Agent network only | Each primary/child probe has only its own key; no operator/tool key or database mount |

The pilot does **not** start the older unauthenticated operator console. Its operator interface is the authenticated CLI. Do not expose the gateway port externally. Requests are signed but local HTTP is not encrypted.

## Run the automated evaluation

```sh
scopedact-pilot evaluate --output pilot-results/evaluation.json
python pilot/verify_isolation.py
scopedact-pilot export --output pilot-results/evidence.json
```

The evaluation checks 17 behaviors: permitted read; denied other-ticket access; denied simulated delete; approval hold; denied agent approval; denied agent task issuance; exact review content; digest mismatch; approval; content substitution; approved execution; replay; one persisted comment; matching receipt; revocation; and event-chain integrity, plus task creation.

**The evaluation harness intentionally holds both roles and programmatically approves its synthetic proposal. It is not an untrusted agent or a human evaluation.** The separate agent-probe container checks operator access denial and lack of a network path to the protected service.

Every evaluation creates a new task and appends one synthetic comment. Ticket versions and evidence persist. No real model is used; malicious action proposals are deterministic. The backend limits each synthetic ticket to 100 comments.

## Try a manual operator approval

Create an assigned task as operator:

```sh
scopedact-pilot create-task --resource ticket:T-100
```

Copy the returned task ID into TASK_ID. Read the ticket as agent:

```sh
TASK_ID='COPY_TASK_ID'
scopedact-pilot invoke --task-id "$TASK_ID" --action read --resource ticket:T-100
```

Note the returned `value.version`. Use that integer in the next JSON object (the example assumes version 1; replace it with the actual current version):

```sh
REQUEST_ID="request:manual-$(date +%s)"
UPDATE_JSON='{"text":"Please try the documented sandbox login steps.","expected_version":1}'
scopedact-pilot invoke --task-id "$TASK_ID" --request-id "$REQUEST_ID" \
  --action update --resource ticket:T-100 --input-json "$UPDATE_JSON"
```

Expected: `APPROVAL_REQUIRED`, `executed: false`.

As the operator, inspect the full canonical proposal:

```sh
scopedact-pilot review --request-id "$REQUEST_ID"
```

Read the task, actor, resource, exact text, and expected version. Copy its digest only if you approve that exact operation:

```sh
REVIEW_DIGEST='COPY_REVIEWED_DIGEST'
scopedact-pilot decide --request-id "$REQUEST_ID" --digest "$REVIEW_DIGEST" --approve
```

Then repeat the original invoke command with the same task, request ID, and input. It should execute once. Changed input is denied. Repeating a completed request does not append again. To reject instead, use `--reject`.

Approval expires five minutes after the decision. Tasks expire after 15 minutes. A version conflict requires a fresh read and a new proposal/approval; do not silently change the reviewed version.

## Intervention and uncertain results

```sh
scopedact-pilot control --task-id "$TASK_ID" --operation pause
scopedact-pilot control --task-id "$TASK_ID" --operation resume
scopedact-pilot control --task-id "$TASK_ID" --operation revoke
scopedact-pilot reconcile --request-id "$REQUEST_ID"
```

Within this single-process pilot, control changes and synchronous dispatch are serialized. Revocation waits for an active call to return; once acknowledged it blocks subsequent calls. It does not undo prior updates or cancel in-flight operations.

If the gateway loses a response after a tool update, the request remains unknown and is not retried automatically. `reconcile` queries the tool's independently stored idempotency receipt and verifies its fingerprint. A matching receipt can mark an unknown claim `reconciled_success`. No receipt does not prove non-execution while a backend call may be in flight. Do not resubmit under a new ID without investigating.

## Persistence and stopping

```sh
docker compose -f compose.pilot.yaml restart
docker compose -f compose.pilot.yaml up -d --wait
docker compose -f compose.pilot.yaml down
```

Named volumes retain gateway evidence and ticket data. Keep the same secret files when restarting. The prototype does not provide automatic backup or multi-process failover. `down` stops the pilot without deleting volumes.

## Running without Docker

After installation and init, use two terminals in the repository directory:

```sh
scopedact-pilot backend
```

```sh
SCOPEDACT_ALLOW_LOCAL_HTTP=1 scopedact-pilot gateway
```

Use the same CLI operations from a third terminal. This mode exercises real HTTP but **does not provide Docker's process/network separation**. The host operator owns all four secret files; do not run untrusted agent code as that host user.

## Configuration

All secrets are file references, never command-line key values:

- `SCOPEDACT_AGENT_KEY_FILE`, `SCOPEDACT_OPERATOR_KEY_FILE`, `SCOPEDACT_TOOL_KEY_FILE`
- `SCOPEDACT_GATEWAY_URL`: client gateway origin; default `http://127.0.0.1:8870`
- `SCOPEDACT_TICKET_URL`: trusted connector origin, not an agent-supplied URL
- `SCOPEDACT_DATABASE`: service-specific SQLite path
- `SCOPEDACT_BIND`, `SCOPEDACT_PORT`: service bind settings
- `SCOPEDACT_ALLOW_LOCAL_HTTP=1`: explicit opt-in for loopback/private pilot transport
- `SCOPEDACT_PILOT_PORT`: Compose host port override; set matching client gateway URL

## Scope for an organization

An organization can evaluate this pilot in a controlled Docker environment using synthetic tickets, without granting cloud or ticketing-system credentials. Connecting its own system is a separate adapter exercise: implement the contract in CONNECTOR_DEVELOPMENT.md, verify credentials stay behind the gateway, and rerun the security and recovery tests. Do not treat this artifact as approval to use sensitive organizational data.
