# Current limitations — v0.14.1

These boundaries apply to the named components in this release. The [capability matrix](CAPABILITIES.md) distinguishes implemented controls from planned integrations.

## Authenticated ticket pilot limitations

- Synthetic tickets and scripted proposals; no live model or third-party ticket platform is exercised by the pilot.
- Separately authenticated development roles use HMAC keys. These establish possession of configured secrets, not enterprise human or workload identity. The trusted host/Docker administrator can access every key and database.
- Delegation exposes one parent-to-child hop, exact action/resource permission subsets, and bounded expiry. It has no multi-parent authority, semantic intent verification, or advanced delegation graph analysis.
- Child actions recheck ancestor pause, revocation, and expiry. Authority can be revoked during an active workflow, preventing subsequent protected actions. In-flight calls are not canceled or undone. One gateway process serializes dispatch and intervention; this is not distributed revocation.
- Exact-content approval has a five-minute default TTL. It cannot override later task/grant or ancestor restrictions. Policy-version binding is not implemented.
- Durable request claims prevent repeat dispatch with the same ID. The backend adds idempotency receipts and optimistic ticket versions; uncertain updates can be reconciled by the operator. This is not exactly-once network execution. A new request ID represents a new operation.
- The REST connector supports fixed ticket routes, not arbitrary APIs configured without code.
- Docker isolation is tested for the supplied primary/child containers by backend service name and direct IP. The non-Docker path lacks that separation. The gateway is published on loopback; HTTP signing does not encrypt traffic.
- SQLite state and receipts survive tested service restarts. This does not establish backups, host-failure recovery, replication, or high availability.
- Proposal content and outcomes remain plaintext in local databases. Default evidence exports redact bodies/read results but retain potentially sensitive metadata. Use synthetic data.
- Local event hash chains are not immutable evidence, signatures, or trusted timestamps. A privileged actor can rewrite the whole chain. Nonces and evidence accumulate without a retention service or comprehensive denial-of-service controls.

See [pilot security](PILOT_SECURITY.md) and [current validation](VALIDATION_0.14.1.md).

## Legacy workspace and laboratory limitations

These are separate optional paths, not the authenticated ticket pilot above.

- The workspace console/dashboard lacks user authentication and must remain on loopback. Local upstream-authority records and caller/reviewer strings do not establish enterprise identity.
- The procurement lab uses localhost services in one process and a public example HMAC key. It provides protocol demonstrations, not OS isolation.
- Legacy lifecycle paths have canonical request binding and durable execution claims, but do not provide the ticket pilot's separate approval TTL, backend idempotency receipts, reconciliation endpoint, authenticated child roles, or ancestor task-pause propagation. Ancestor grant revocation and expiry are checked.
- The process-local SDK does not coordinate multiple processes or sandbox agent code. Its caller identities are trusted integration inputs.
- Workspace path checks reject symlinks but do not protect against hostile concurrent filesystem changes. Legacy synthetic procurement data can reset between commands.
- Optional live-model and read-only AWS examples have mocked external-I/O tests; they do not establish live-model effectiveness or cloud-account safety. Separately retained HMAC evidence anchors are not third-party attestations.

## Production capabilities not implemented anywhere

Enterprise IdP/workload identity, credential rotation infrastructure, multi-tenancy, distributed cancellation/enforcement, transactional cross-service guarantees, production TLS deployment, immutable external evidence storage, policy-version binding, structured task-intent enforcement, and privilege-drift remediation remain future work. MCP and general-purpose cloud/ticketing adapters are not implemented integrations.

The project is a developer preview for focused evaluation. Included scenario pass rates apply only to the tested fixtures, not arbitrary attacks or deployments.
