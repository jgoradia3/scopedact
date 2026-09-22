# Public implementation boundary

ScopedAct v0.14.1 is a practical reference implementation built from established authorization and systems patterns. Its delegated ticket scenario uses only single-parent permission-subset narrowing, expiry bounds, authenticated role keys, and recorded parent/child links.

It does not implement advanced graph-based authority propagation, semantic intent inference, runtime attestation, automated least-privilege remediation, distributed enforcement, or unpublished research-specific mechanisms. The new lineage report renders stored relationships; it is not graph-constraint research.

Evaluate the repository only against its implemented, documented, and tested behavior. Planned capabilities and excluded mechanisms must not be represented as completed work.
