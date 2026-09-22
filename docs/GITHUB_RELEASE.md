# Public review release checklist — v0.14.1

The ZIP is a local review artifact. Publishing it, enabling private vulnerability reporting, and verifying hosted CI are separate steps that have not been performed here.

1. Upload the clean source tree to the intended repository. Exclude runtime secrets, SQLite databases, generated evaluation output, environments, build directories, and caches.
2. Follow [the reviewer guide](REVIEW_GUIDE.md) from a fresh environment and record the release checksum.
3. Inspect the GitHub Actions `tests` workflow. Verify every Python 3.10–3.13 matrix job and the Docker ticket-pilot job succeeds for the exact release commit. The Python job includes explicit SQLite ownership checks; the Docker job includes both evaluations, both isolation probes, and post-restart evaluations.
4. Configure a private vulnerability-reporting route and confirm its visibility. Update SECURITY.md only with a verified reporting method.
5. After successful hosted execution, link the actual workflow run and add a CI badge using the verified repository URL. Do not replace “configured but not verified” with a success claim before then.
6. Tag the reviewed commit `v0.14.1`, create a developer-preview release, and attach the source archive and SHA-256 checksum. Confirm the archive matches that commit's source.
7. Invite a small number of reviewers to evaluate that exact version using synthetic data. Record what they actually tested and obtain permission before quoting or attributing feedback.

Do not treat a local test run, configured workflow, or draft review invitation as evidence of hosted CI, external adoption, or reviewer endorsement.
