> Legacy workspace/laboratory guide. Current ticket-pilot controls and trust boundaries are described in [pilot security](PILOT_SECURITY.md) and [the reviewer guide](REVIEW_GUIDE.md).

# Threat Model

## Security properties demonstrated

For the predefined synthetic lifecycle, a task grant is issued only when each
requested permission exists in the initiator's local upstream-authority record.
A service action executes only when the task is active, the request is not a
terminal replay, the tool binding matches, the acting principal owns the grant,
the exact action-resource permission is present, and any configured approval is
satisfied.

## In scope

- An agent proposes an action not listed in its grant.
- Untrusted invoice text encourages a more privileged action.
- A sub-agent is proposed with permissions absent from its single parent grant.
- A caller uses a grant belonging to a different principal.
- A grant is missing, expired, inactive, or revoked.
- A reviewer needs to reconstruct the demonstrated execution chain from audit fields.
- An operator pauses, resumes, revokes, or closes a task.
- A sensitive action waits for durable approval.
- A completed request identifier is replayed after restart.

## Trusted components

- Python runtime and host running the demonstration
- Authorization evaluator and gateway code
- SQLite lifecycle and grant registries for the MVP
- Protected local tool or optional connector
- Test fixtures and fixed clock

## Out of scope

- Compromise or bypass of the gateway/evaluator
- Tampering with in-memory state or audit files
- Authentication of humans, reviewers, or workloads
- Cryptographic integrity, replay protection across processes, or key management
- Distributed races, stale evaluators, policy propagation, and automated rollback
- Collusion, multi-parent delegation, or aggregate authority
- Semantic correctness of user intent
- Prompt-injection detection or model alignment
- Production availability, privacy, and regulatory compliance

## Important interpretation

The malicious-instruction scenario does not claim to detect prompt injection. It intentionally allows a scripted agent to propose the disallowed action and shows that an external permission check blocks execution.
