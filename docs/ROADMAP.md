# Roadmap

ScopedAct is a reference implementation for independently enforcing and attributing agent task authority. The current review milestone is deliberately bounded: task scope, exact approval, one-parent delegation, lineage, subsequent-action revocation, and reproducible isolated evaluation.

## Next: independent review

Collect reproducible findings, fix control defects, and verify documentation against observed behavior. Do not add integrations solely to increase feature count. Public CI should run when the repository is published; this local release does not claim hosted CI success.

## Optional integration milestones

- MCP tool interception and one real agent-framework example, preserving a deterministic no-model test path.
- Standards-based workload/operator identity validation, issuer/subject/audience checks, short-lived credentials, and key rotation.
- Operator-approved structured task constraints and policy-version binding. Do not claim semantic inference of arbitrary human intent.
- A real ticketing or cloud adapter when an evaluator has a concrete use case and a safe test environment.

## Later capabilities

- External evidence verification, signed exports, retention/redaction controls, and trusted anchoring.
- Multi-instance concurrency, distributed revocation, long-running operation controls, TLS deployment, and recovery tooling.
- Permission-use observation and shadow recommendations as a separate module, with review before restriction and rollback.

Advanced delegation-graph analysis, semantic intent processing, runtime attestation, and unpublished research mechanisms remain outside this public implementation. Roadmap entries are not release promises or claims of implemented behavior.
