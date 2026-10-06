> Historical validation snapshot. Results and publication status below apply to that recorded run. See [the latest review record](STABILIZATION_REVIEW.md) for subsequent checks.

# STG-AUTH-204 validation — 0.18.0

Maintainer-run validation on October 3, 2026. Synthetic fixtures and automated test
approvals were used. This is not independent adoption evidence or a human review of
the proposed report.

- Full resource-checked suite: 152 tests passed; 2,086 SQLite connections opened,
  zero unclosed.
- Scenario tests cover an archived-runbook choice, modified evidence, atomic fixture
  seeding, restricted reads, approval followed by pause, terminal denial, a new proposal
  requiring new approval, and duplicate execution prevention.
- Source distribution and wheel built; the installed wheel includes the incident
  fixtures and `scopedact-incident` command.
- The installed CLI completed the workflow against the Docker gateway: two runbook
  candidates, selection, evidence reads, held report, two restricted-read denials,
  pause and denied retry, resume and denied replay, a fresh approved proposal, one
  applied report update, duplicate denial, and metadata export.
- Final task evidence: 18 document attempts, 11 completed (10 reads plus one update),
  5 blocked, 2 held, 0 uncertain; report version 2; local event-chain verification passed.
- The first Docker task-creation attempt returned HTTP 503. After checking the healthy
  gateway and readable catalog, a subsequent start succeeded. The transient cause was
  not established; this result is not a claim of production deployment reliability.
- JavaScript syntax checked. The signed-in console layout was not re-verified: the
  earlier browser permission to load the operator key was declined.
- The optional Ollama path for this incident was documented, not live-model validated.
  The report in this evaluation was scripted for the packaged fixture.
- GitHub CI configuration includes the new harness steps; hosted CI has not run on
  this unpublished source state.

See the [reviewer workflow](INCIDENT_EVALUATION.md) for exact commands and boundaries.
