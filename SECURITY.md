# Security policy

ScopedAct is developer-preview software for controlled, synthetic-data evaluation.
The current incident lab uses authenticated local sessions, signed agent requests,
explicit task permissions and approval-gated changes. These controls do not establish
enterprise identity, production readiness or protection from every prompt injection.

Reviewers run their own copy. Publishing this repository does not grant access to
the maintainer's computer. Keep supplied interfaces on loopback and do not commit
or share credentials, sign-in links, databases or private journals. Native mode
shares your OS account and is not a sandbox. Docker provides the specific isolation
boundaries documented in [local security](docs/LOCAL_SECURITY_BOUNDARY.md).

The original file-workspace console (`scopedact serve`) has no user authentication.
The older procurement lab includes a public example key. These separate reference
examples do not inherit the current console's session protections.

## Reporting

For non-sensitive defects, open a minimal GitHub issue with the commit/version,
environment, expected behavior and a synthetic reproducer. Do not include real
customer data or production credentials.

For sensitive findings, use GitHub private vulnerability reporting **if enabled** on
the repository. If no private route is available, request one without posting exploit
details or secrets. This policy does not claim that a private reporting route has
been verified or promise a response SLA.

See [threat model](docs/THREAT_MODEL.md), [limitations](docs/LIMITATIONS.md) and
[ticket-pilot boundaries](docs/PILOT_SECURITY.md) for component-specific scope.
