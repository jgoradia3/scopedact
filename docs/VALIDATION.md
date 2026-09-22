# Local validation — v0.12.0

Validated September 21, 2026 on macOS, Python 3.11.

- Full unittest suite: **90 tests passed** (original 75 retained, 15 new tests).
- Signed workspace HTTP integration: read allowed, delete denied, root-folder listing allowed, approval-gated append resumes, changed input rejected, changed task rejected, direct unauthenticated tool request rejected.
- Deterministic concurrency tests: both ordinary requests and approved resubmissions dispatch only once per request ID.
- Failure checks: side-effect-then-timeout prevents retry; retained claims survive store reopening; dispatch evidence failure prevents tool invocation.
- Delegation and workspace checks: ancestor revocation/missing ancestor denied; internal symlinks and parent traversal rejected.
- Source distribution and wheel built successfully.
- Wheel installed in a fresh virtual environment; version, init, doctor, SDK quickstart, and signed HTTP approval-substitution probe ran outside the source checkout.
- Browser visual inspection: exact canonical request and escaped input visible next to approval controls; execution-claim states visible. The visual check used a synthetic rendered snapshot, not a full browser click-through of the operator flow.

Not tested: hosted GitHub Actions, Python versions other than 3.11, container deployment, real models, cloud services, adversarial local filesystem races, or a production security assessment. Docker remains the inherited offline-tour setup.

Review of the starting archive verified SHA-256:
`6927a696d30e32cf2c842c9f1985e889b0b1b9af17903095e6935c29ae2873ec`.

This release is suitable for requesting independent evaluation of its documented local-preview scope. A passing suite is not proof of production security.
