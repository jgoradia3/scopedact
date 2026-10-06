# Release checklist

Use the exact commit being released. Do not infer release readiness from an older
version's successful checks.

1. Run the checks in [Contributing](../CONTRIBUTING.md) and follow [native setup](NATIVE_REVIEW.md) from a fresh installation. Record live-model outcomes separately from automated tests.
2. Check the source archive contains only intended source, tests, documentation and synthetic assets. Exclude credentials, databases, model journals, environments and build output.
3. Verify all seven hosted jobs for the exact commit: Python 3.10–3.13, ticket pilot, managed workspace and live incident lab. A configured workflow is not a successful run.
4. Confirm package metadata and `scopedact --version` agree. Update the changelog for a new version; never reuse an existing release tag for different source.
5. Confirm the reporting method in [SECURITY.md](../SECURITY.md) is available. Review limitations and setup instructions for accuracy.
6. Tag the reviewed commit with its actual package version, create the developer-preview release, and attach a clean source archive and SHA-256 checksum matching that commit.
7. Invite focused technical review using [the review guide](REVIEW_GUIDE.md). Record what reviewers actually ran; do not equate a code review or video view with organizational adoption.

These are publication steps, not a claim that a new tag or release already exists.
