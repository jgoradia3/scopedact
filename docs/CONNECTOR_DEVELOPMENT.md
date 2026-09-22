# Developing a contextual connector

The existing `Connector` protocol remains compatible. `ExecutionContext` and `ContextConnector` in `scopedact.connectors` add request ID, task ID, authenticated actor label, and exact reviewed input. The ticket pilot provides `TicketRestConnector` as a concrete REST adapter.

## Required behavior

1. Map a small action set to fixed methods and paths. Never accept an arbitrary agent-supplied URL, method, credential, or redirect destination.
2. Parse and canonicalize resource identifiers before constructing URLs. Ticket resources match `ticket:T-<digits>` only.
3. Validate typed inputs. For updates, the pilot requires exact text and an expected ticket version. Read operations accept no input.
4. Use a backend-only credential from a secret file. The agent must not share the connector's network or credential boundary.
5. Preserve the canonical request ID as the backend idempotency key. The backend must bind that key to the resource and body, and persist the mutation and receipt atomically.
6. Bound connection time, response size, and payload size. Disable inherited proxies and redirects that could forward credentials. Verify TLS for remote origins.
7. Categorize failures without assuming timeout means no side effect. Provide a read-only reconciliation operation that returns a receipt bound to the exact operation.
8. Redact credentials and sensitive payloads in diagnostic errors and exported evidence.

The included backend contract is:

| Route | Meaning |
|---|---|
| GET /tickets/T-100 | Returns id, title, version, comments |
| POST /tickets/T-100/comments | Accepts text and expected_version; Idempotency-Key required |
| GET /operations/request:ID | Returns found, fingerprint, and result |

All non-health backend routes require the tool bearer credential. Update fingerprint is SHA-256 of canonical JSON containing `resource` and `input` (sorted keys, compact separators, no NaN). The receipt and update share one SQLite transaction. Repeating an identical operation returns the original receipt; a changed fingerprint or version mismatch returns 409 without mutation.

`bind(context)` adapts the contextual connector to the existing gateway's two-argument tool interface. The gateway, not the connector or agent, enforces task scope and approval before dispatch. Registering a connector does not itself establish a security boundary.

## Extension tests

At minimum, run legitimate calls, wrong resource, unapproved update, changed approved input, concurrent replay, stale version, lost response after mutation, backend restart, gateway restart, direct access, key separation, URL injection, redirect, and receipt mismatch tests. A third-party API that lacks idempotency or operation receipts needs its own recovery design; do not claim exactly-once execution from the gateway alone.

This is a constrained HTTP/REST implementation, not a universal REST proxy. MCP remains future work.
