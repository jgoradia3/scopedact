# Historical release notes

These describe the implementation and publication status **at each past release**, not the current product. For current setup use [native review](NATIVE_REVIEW.md); for current scope see [capabilities](CAPABILITIES.md). Validation records remain separate so their original results and limitations are preserved.

## v0.12.0 review release

The v0.11.0 durable gateway could reuse an approved request ID under a different task and could dispatch the same ID concurrently. This release binds each request to immutable canonical content and atomically reserves it before execution. It retains pending input for operator review and exposes durable execution-claim states.

The root folder listing example now passes resource validation. Delegation evaluation checks ancestor grants. Event-chain appends are serialized. The SDK serializes calls within one gateway instance.

### Behavior and failure contract

A mismatched canonical request is denied without altering the original approved operation. A concurrent call receives REQUEST_IN_PROGRESS. A completed or uncertain execution cannot be dispatched again under the same ID. If execution or result persistence fails, state becomes unknown when storage permits; abrupt process death may leave evaluating. Neither is automatically retried. The operator must reconcile the actual tool effect before creating a replacement request.

Authorization is rechecked when a pending request resumes. Approval cannot expand permission. Approve/reject decisions are terminal. Task/grant checks limit approval lifetime; separate approval expiration remains future work.

### Scope

No REST/MCP connector, remote authentication, production secret store, isolated deployment, or automatic recovery was added. Docker remains the existing offline-tour configuration. This release is intended for independent local technical review, not sensitive production use.

See VALIDATION.md for performed checks and LIMITATIONS.md for trust boundaries.

## v0.13.0 — Isolated support-ticket pilot

ScopedAct now includes a concrete REST-backed workflow that an independent reviewer can run with synthetic data: read an assigned ticket, propose an update, review and approve exact content as a separate operator, execute once, intervene, and export evidence.

### New components

- Contextual connector contract preserving request/task identity and reviewed input.
- Fixed-route REST ticket connector with response limits, timeout, no inherited proxies, and no redirects.
- Persistent synthetic backend with atomic idempotency receipts and expected-version checks.
- Separate signed agent and operator API roles, authenticated CLI review/approval, and five-minute approval expiry.
- Read-only reconciliation of uncertain update results using backend receipts.
- Redacted evidence export and a deterministic 17-check evaluation harness.
- Compose deployment with private backend network, no backend host port, file-based secrets, read-only container filesystems, and non-root application processes.
- Agent-only network probe testing both service-name and direct-IP access.

### What this enables

Invite a reviewer to run a controlled synthetic pilot, challenge the controls, inspect the records, and suggest integration requirements. The pilot makes real HTTP calls and persists real synthetic updates. It does not yet connect to Jira, ServiceNow, AWS, MCP, or an organization's identity provider.

The older local workspace remains available. The pilot's authenticated CLI does not change the authentication status of the old operator console.

### Validation

See PILOT_VALIDATION.md. No independent evaluation, organizational adoption, or production certification is claimed.

## v0.14.0 — Bounded delegation and review clarity

This release addresses the shared review gap in v0.13: the authenticated ticket pilot now demonstrates primary-agent to child-agent delegation and attributable tool calls. It preserves the ticket workflow, exact approvals, idempotency, recovery, and isolated deployment.

### Changes

- Add a separately keyed diagnostic child role and a primary-only delegation endpoint.
- Enforce one-parent subset permissions, inherited initiator, bounded expiry, and one exposed delegation hop.
- Commit child grant, lifecycle record, and issuance evidence atomically.
- Recheck ancestor pause/revocation/expiry on child actions.
- Record authenticated actor, grant actor, parent, parent task, delegation ID, tool, decision, and outcome in attributed events.
- Add operator-only JSON and readable lineage reports and a 19-check delegated evaluation.
- Run isolation probes for both primary and child containers, each with only its own key.
- Add VISION.md, a capability matrix, architecture diagram, and one focused reviewer guide.

### Feedback disposition

| Feedback | Disposition |
|---|---|
| Visible bounded delegation | Implemented in the main ticket pilot |
| End-to-end delegated lineage | Implemented from authenticated requests and stored grants |
| Precise revocation language | Documentation states that subsequent protected actions are denied; no in-flight cancellation claim |
| Provider-neutral project vision | Added; ticket service described as one reference workflow |
| Capability status and legacy boundaries | Explicit tables and current reviewer guide |
| Precise REST/isolation/persistence claims | Limited to fixed-route connector and tested container/restart behavior |
| Public CI and release visibility | Updated workflow included; publication and hosted execution not performed here |
| MCP/live model, OIDC, task context, policy binding | Explicit future milestones, not represented as complete |
| Advanced graph/SOR/research mechanisms | Deliberately excluded from this bounded public milestone |

The reviews differed on which larger future integration should come next. This release implements their overlapping near-term recommendations without claiming an enterprise platform. No reviewer endorsement or independent validation of v0.14 is implied.

## v0.14.1 — Public-review preparation

This patch addresses the two v0.14.0 reviews without adding another integration or expanding the authority model.

- Rewrite architecture around the current ticket pilot and separate legacy evaluation paths.
- Replace accumulated limitations with current pilot, legacy, and unimplemented production capabilities.
- Clarify development-role HMAC identity and revocation of subsequent actions in the public documentation.
- Explicitly close registry and short-lived SQLite connections in runtime paths and test fixtures, including error paths. SQLite transaction contexts commit/roll back but do not close the connection.
- Add a portable SQLite ownership checker to the Python CI matrix.
- Add a regression scenario that approves a child update, pauses or revokes its parent, resumes the exact approved request, and verifies denial, unchanged ticket state, and no backend mutation receipt.
- Preserve the 17-check ticket and 19-check delegation evaluations.

Hosted CI, GitHub publication, a public badge, and a release tag remain publication steps. This local package does not claim they have occurred. See [validation](VALIDATION_0.14.1.md) and [publication checklist](GITHUB_RELEASE.md).

v0.14.0 remains unchanged as an earlier review artifact; v0.14.1 identifies this patch unambiguously. Further feature work should follow concrete external findings.
