# Technical review guide

Evaluate whether ScopedAct's recorded authorization decisions match actual protected execution. The staging incident is a test environment for these controls, not a claim of production readiness.

## Start with one investigation

Follow the [reviewer walkthrough](REVIEWER_QUICKSTART.md), using either [native setup](NATIVE_REVIEW.md) or the [Docker lab](LIVE_INCIDENT_LAB.md). Native mode supports functional review; Docker adds the documented container/network boundaries.

Choose one question:

- When a request is outside the task grant, is it denied before protected execution?
- After a denial, does continuation retain exactly the same permissions?
- Does approval bind the exact proposal, and do later authority checks still apply?
- Does the map agree with the request history and execution evidence?
- Can you distinguish a finished investigation, an applied change, and verified recovery?

The local model may not attempt the action you expect. Report that outcome honestly. Use the separate deterministic evaluations when testing a particular control must not depend on a model's choice.

## Deeper control checks

The [ticket pilot](TICKET_PILOT.md) and [delegation guide](DELEGATION.md) provide commands for scripted HTTP evaluations of approval, replay protection, reconciliation and constrained delegation. Their expected checks are defined in those guides. They do not constitute live-model or independent-use results.

For an implementation review, start with [architecture](ARCHITECTURE.md), [security boundaries](PILOT_SECURITY.md), [limitations](LIMITATIONS.md) and [validation](STABILIZATION_REVIEW.md). Check ancestor revocation, approval substitution, duplicate requests, and uncertain remote outcomes. Integrations beyond the supplied adapters require separate assessment.

## Submit a useful finding

A GitHub issue can include:

```text
Commit/version:
OS, Python, native or Docker:
Ollama/model (if used):
Access profile and exercise:
Steps to reproduce:
Expected authorization / execution:
Observed authorization / execution:
Evidence or request IDs (sanitized):
Why this matters in your workflow:
```

Describe what you actually ran, including unsuccessful or incomplete results. If you only inspected code or watched the video, say so. No positive endorsement is requested.

Inspect exports before attaching them. Do not share keys, access links, private journals or databases. For sensitive vulnerabilities, follow [SECURITY.md](../SECURITY.md) rather than a public issue.
