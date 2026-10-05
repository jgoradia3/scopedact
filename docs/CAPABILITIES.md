# Capability status

The primary reviewer path is the [live-model incident investigation](REVIEWER_QUICKSTART.md), available through native or Docker setup. The separate ticket pilot provides deterministic approval and delegation evaluations. Capabilities below have deployment-specific boundaries.

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
| Local model integration | Implemented, bounded | Ollama chooses tools for one synthetic incident against live services; no scripted fallback or guaranteed repair. MCP and external agent-framework adapters remain future work |
| Reviewer console | Implemented | Access profiles, actual request map, approval controls, pause after denial and evidence export |
| Native launcher | Implemented | macOS/Linux, loopback services under one OS account; no container or same-user isolation |
| OIDC/JWT and key lifecycle | Planned | Issuer/subject/audience validation, rotation, short-lived workload credentials |
| Task intent/context | Partial | Local incident catalog and configured policy produce explicit grants within upstream authority; prompt text cannot expand scope, and arbitrary intent is not inferred |
| Policy-version binding | Planned | Approval invalidation on policy/context changes |
| Distributed cancellation/HA | Planned | Current revocation does not cancel in-flight actions or coordinate multiple gateway instances |
| Privilege-drift observation | Planned | Separate observational/shadow module, not current enforcement behavior |
| Real ticketing/cloud adapters | Planned | No Jira, ServiceNow, or multi-cloud production integration |
| Hosted public CI | Verified for initial publication | [Run 35798797312](https://github.com/jgoradia3/scopedact/actions/runs/35798797312) passed Python 3.10–3.13 and the Docker pilot job; see Actions for current status |

Implemented is not equivalent to production-ready, independently reviewed, or adopted. See [current validation](STABILIZATION_REVIEW.md) and [historical ticket validation](VALIDATION_0.14.1.md) for checks actually performed.
