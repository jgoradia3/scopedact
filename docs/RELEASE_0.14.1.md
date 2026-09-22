# v0.14.1 — Public-review preparation

This patch addresses the two v0.14.0 reviews without adding another integration or expanding the authority model.

- Rewrite architecture around the current ticket pilot and separate legacy evaluation paths.
- Replace accumulated limitations with current pilot, legacy, and unimplemented production capabilities.
- Clarify development-role HMAC identity and revocation of subsequent actions in the public documentation.
- Explicitly close registry and short-lived SQLite connections in runtime paths and test fixtures, including error paths. SQLite transaction contexts commit/roll back but do not close the connection.
- Add a portable SQLite ownership checker to the Python CI matrix.
- Add a regression scenario that approves a child update, pauses or revokes its parent, resumes the exact approved request, and verifies denial, unchanged ticket state, and no backend mutation receipt.
- Preserve the 17-check ticket and 19-check delegation evaluations.

Hosted CI, GitHub publication, a public badge, and a release tag remain publication steps. This local package does not claim they have occurred. See [validation](VALIDATION_0.14.1.md) and [publication checklist](GITHUB_RELEASE.md).

v0.14.0 remains unchanged as an earlier review artifact; v0.14.1 identifies this patch unambiguously. Further feature work should follow concrete external findings.
