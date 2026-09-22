# Capability status — v0.14.1

| Capability | Status | Actual scope |
|---|---|---|
| Task-scoped authority | Implemented | Exact action/resource pairs in expiring task grants |
| External enforcement | Implemented | Gateway authorizes before fixed-route REST tool dispatch |
| Sensitive-action approval | Implemented | Canonical request binding, reviewed digest, TTL, separate operator role |
| Single-parent delegation | Implemented | Primary-to-diagnostic child, subset and expiry bounds, one hop in pilot |
| Delegated lineage | Implemented | Stored initiator/parent/child relationships and authenticated action evidence; CLI report |
| Intervention | Implemented | Pause/resume/revoke and ancestor checks before later calls in one gateway process |
| Duplicate/uncertain execution | Implemented | Durable claims, backend idempotency receipts, manual reconciliation |
| Isolation | Implemented/tested deployment | Included Docker primary and child containers cannot reach ticket backend by name/IP |
| Persistence | Implemented/tested deployment | Local SQLite and named volumes across tested service restarts |
| Provider-neutral connector contract | Implemented | Contextual Python protocol plus a fixed-route REST ticket adapter |
| Identity assurance | Partial | Distinct signed HMAC role requests; no corporate IdP or workload identity verification |
| Evidence protection | Partial | Local hash chain and redacted exports; not immutable third-party evidence |
| Real autonomous agent integration | Planned | Scripted requests are current reference path; no live model/MCP demonstration yet |
| OIDC/JWT and key lifecycle | Planned | Issuer/subject/audience validation, rotation, short-lived workload credentials |
| Task intent/context | Planned | Explicit operator-approved structured constraints; no semantic intent inference |
| Policy-version binding | Planned | Approval invalidation on policy/context changes |
| Distributed cancellation/HA | Planned | Current revocation does not cancel in-flight actions or coordinate multiple gateway instances |
| Privilege-drift observation | Planned | Separate observational/shadow module, not current enforcement behavior |
| Real ticketing/cloud adapters | Planned | No Jira, ServiceNow, or multi-cloud production integration |
| Hosted public CI | Configured, not verified here | Workflow included; requires publication and successful hosted execution |

Implemented is not equivalent to production-ready, independently reviewed, or adopted. See VALIDATION_0.14.1.md for checks actually performed.
