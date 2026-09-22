# Security policy

ScopedAct v0.14.1 is experimental developer-preview software for synthetic-data evaluation. The authenticated ticket pilot uses separate HMAC development-role keys and a tested Docker network boundary. These controls do not establish enterprise identity or production readiness. See [current limitations](docs/LIMITATIONS.md) and [pilot trust boundaries](docs/PILOT_SECURITY.md).

The legacy workspace console has no user authentication. The procurement lab includes a public evaluation key and runs local HTTP services without OS isolation. Keep all evaluation interfaces on loopback; do not expose them publicly or use production credentials or customer data.

For non-sensitive defects, open a minimal GitHub issue with the version, expected behavior, and synthetic reproducer. For sensitive findings, use GitHub's private vulnerability reporting only if it is enabled on the published repository. If no private channel is available, request a private contact route without posting exploit details or secrets. Private reporting and hosted security support have not been verified for this local release.

No production-service SLA or security-support commitment is provided.
