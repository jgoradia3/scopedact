# Pilot trust boundaries and limitations

## Implemented boundary

- Independent HMAC keys authenticate a primary agent, a diagnostic child, and a single operator role. Signed method/path/body, timestamp window, and durable nonce checks protect incoming requests. Caller-supplied reviewer names are not accepted.
- Only the operator may issue root task grants, approve/reject, intervene, inspect canonical requests, reconcile, or export evidence.
- Agents can propose actions only on issued tasks. The primary can narrow its root grant into a child grant; the child cannot delegate further. Approval cannot expand permissions.
- Docker provides separate gateway and backend processes. The backend is on an internal network and has no published host port. Each primary/child probe has only the front network and its own key.
- The container initializer reads Docker secret mounts and prepares state as root, uses narrowly listed startup capabilities to read owner-only secret mounts and prepare state, then drops to UID/GID 10001 before running the application. Runtime effective capabilities are empty. Root filesystems are read-only and credentials are copied into private tmpfs, not image layers.
- Backend idempotency and optimistic version checking prevent duplicate mutations and overwriting an unreviewed ticket version.
- In the single gateway process, invocation and operator intervention share a lock. An acknowledged revocation precedes later dispatch. In-flight calls are not canceled.

## Explicit limitations

- Synthetic ticket service, scripted proposals, two configured agent roles and one operator. No corporate IdP, MFA, multiple tenants, credential rotation service, or real ticketing-provider integration.
- HMAC authenticates possession of a role key, not a verified person. The trusted host and Docker administrator can access all secrets and state. Do not give an untrusted agent Docker access or the operator's host account.
- The pilot uses HTTP only on loopback/private container networks. Request signing does not encrypt content. Remote exposure requires reviewed TLS and deployment controls; do not bind the host port publicly.
- One gateway process; no horizontal scaling, asynchronous cancellation, distributed revocation, or exactly-once network guarantee. A backend operation can finish after a gateway timeout; reconcile it before considering a new request.
- Receipt evidence is an independently persisted backend record, not a third-party attestation or cryptographic proof. Hash chaining detects certain edits but is not immutable storage.
- Inputs and tool outcomes remain plaintext in local databases for review/reconciliation. Default export removes proposal bodies and read results, but still exposes task identifiers, metadata, and decision history. Use synthetic data.
- No quotas or sophisticated denial-of-service protection; HTTP body sizes and read timeouts are bounded, but client nonces and evidence accumulate. This is a controlled test deployment.
- Existing workspace/legacy commands retain their documented limitations. Running this authenticated pilot does not retrofit authentication onto the old console.
- The evaluation harness holds multiple roles to exercise a deterministic workflow. It is not evidence that an autonomous agent can safely hold operator credentials. The primary and child probes check separate constrained containers instead.

## Delegation scope

The pilot supports one parent-to-child hop. Child calls recheck ancestor grant bounds and lifecycle status, including pause. Parent relationships are read from stored grants, not supplied by the caller. Authority can be revoked during a workflow so subsequent protected actions are denied; in-flight calls are not canceled. There is no multi-parent or advanced graph analysis.
