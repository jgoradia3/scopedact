# v0.14.1 — Review-release cleanup

- Close SQLite connections explicitly and check ownership in CI.
- Verify approved child updates remain blocked after parent pause/revocation.
- Rewrite current architecture and limitations, and clarify release/publication status.

# v0.14.0 — Delegated pilot

- Add separately authenticated child, subset/expiry-constrained delegation, ancestor lifecycle checks, attributed action evidence, and lineage CLI.
- Add delegated evaluation, both-agent isolation checks, reviewer regression tests, capability/vision documentation, and precise security claims.

# v0.13.0 — Support-ticket pilot

- Add a fixed-route contextual REST connector and a persistent synthetic ticket backend.
- Authenticate separate agent and operator roles; bind approval to reviewed digest with expiry.
- Add authenticated CLI review, approval, task control, reconciliation, and redacted export.
- Provide isolated Compose networks, file-based secrets, non-root service execution, and persistent volumes.
- Add a 17-check evaluator, agent network probe, pilot security tests, and deployment documentation.

# v0.12.0 — Review hardening

- Bind durable approval to immutable canonical requests including input.
- Reserve request IDs transactionally before dispatch; block concurrent execution and uncertain retries.
- Show exact approval content and execution-claim state in the console.
- Fix resource validation for root-folder listing and nested workspace paths.
- Serialize event-chain appends and in-process SDK invocations.
- Check delegation ancestors at runtime; reject workspace symlinks before resolution.
- Add security regressions and reviewer documentation.

# Changelog

## 0.11.0 - 2026-08-19

- Added a complete local protected-workspace application as the primary user workflow.
- Added `init`, `doctor`, `serve`, `create-task`, and `invoke` commands.
- Added generated editable authority policy, isolated workspace, and local signing key.
- Added signed list/read/append/delete proposals through the gateway.
- Bound approval decisions to the exact request input hash to prevent post-approval substitution.
- Added path-containment, traversal, symlink, file-size, and input-size safeguards.
- Rewrote the README around installation, user-controlled policy, real tool outcomes, and integration.
- Added application and Docker evaluation guides and expanded end-to-end tests.

## 0.10.0 - 2026-08-19

- Added an installable, documented Python SDK for protecting ordinary callables.
- Added a copy-paste quickstart that proves an out-of-scope action never reaches its function.
- Added Docker and Compose evaluation paths plus contributor Make targets.
- Added GitHub bug, integration-feedback, and pull-request templates.
- Added a release checklist and explicit first external-evaluation protocol.
- Reclassified the project as an alpha Developer Preview and removed `PYTHONPATH` from primary usage.

## 0.9.0 - 2026-08-16

- Added a narrated `tour` command centered on proposal, decision, and execution.
- Reworked agent-client output to separate authorization from HTTP transport success.
- Added a persistent dashboard explanation of the core concepts.
- Added plain-language Start Here, real-versus-simulated, and reviewer-demo documents.
- Repositioned the README around comprehension before installation.

## 0.8.0 - 2026-08-16

- Added a localhost service-boundary lab with separately addressed gateway, protected tool, and operator console.
- Added an independent signed agent client and reviewed task-creation API.
- Added HMAC request integrity, timestamp validation, durable nonce replay rejection, and configured actor binding.
- Added a runtime-only gateway-to-tool credential that blocks direct tool calls.
- Kept sensitive payment pending for real operator approval and explicit client resume.
- Added end-to-end adversarial tests for bypass, tampering, stale requests, replay, wrong clients, self-approval, ungranted resources, and paused tasks.

## 0.7.0 - 2026-08-15

- Added an authority-source contract and signed, expiring local authority bundles.
- Added separately retained signed event anchors and anchor verification.
- Added a reusable connector contract and registry around the AWS example.
- Added guided task creation to the localhost operator console.
- Expanded negative tests for bundle tampering, expiration, anchor tampering, and event-tail deletion.

## 0.6.0 - 2026-08-15

- Added interactive localhost lifecycle and approval controls with CSRF safeguards.
- Added outcome filters, readable timeline, permission chips, connector health, and integrity status.
- Added strict external lifecycle configuration and a deterministic or optional model-proposed multi-step workflow.
- Added basic SHA-256 lifecycle-event hash chaining and verification.
- Added AWS identity preflight and a non-executing exact-command dry run.
- Reframed the package as a cohesive practitioner preview within a broader research program.

## 0.5.0 - 2026-08-15

- Added issuance checks against a durable local upstream-authority source.
- Added durable lifecycle tasks, canonical requests, append-only attempt records, approvals, outcomes, and events.
- Added replay rejection that survives gateway and process restart.
- Added operator pause, resume, revoke, and close transitions.
- Added a complete procurement lifecycle with approval and intervention.
- Added a hands-on task and request workflow for operator evaluation.
- Added a local read-only dashboard and JSON state view.
- Routed the optional read-only AWS example through lifecycle grant issuance.
- Added an operator guide and updated product positioning.
- Expanded the automated suite for issuance, durability, approvals, controls,
  dashboard rendering, hands-on operation, and external-connector routing.

## 0.3.1 - 2026-08-13

- Repositioned the README around practitioner value and rapid evaluation.
- Added a clear product tagline and immediate allow/deny example.
- Separated evaluation, integration, and contribution paths.
- Clarified that tests support review but are not part of ordinary usage.
- Documented the broader authority lifecycle without claiming planned features.
- Added a capability-based roadmap aligned with practical agent governance.
- Strengthened current-capability, production-readiness, and identity-derivation boundaries.

## 0.3.0 - 2026-08-13

- Added a minimal vendor-neutral protected-tool interface.
- Added explicit request-to-tool binding enforcement.
- Added deterministic and optional live-model structured-action proposers.
- Added an optional AWS CLI connector restricted to `iam:GetRole` for one role.
- Added an end-to-end agent proposal, authorization, execution, and audit demo.
- Expanded integration and input-safety tests.
- Documented sandbox-only AWS usage and credential-handling boundaries.

## 0.2.0

- Add strict structured action-request parsing and identifier validation.
- Reject reuse of completed request identifiers.
- Add JSON-configured human approval requirements for sensitive actions.
- Allow approval-pending requests to resume after a human decision.
- Add an optional SQLite registry for durable grants and revocations.
- Add a multi-step invoice and purchase-order reconciliation scenario.
- Expand the deterministic test suite from 13 to 22 tests.
- Generalize publication-boundary documentation.

## 0.1.0

- Initial vendor-neutral task-scoped authorization demonstration.
