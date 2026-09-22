# Start here: ScopedAct v0.14.1

ScopedAct is an experimental reference implementation for task-scoped authority and accountable tool access. Identity establishes who or what is making a request; authority establishes what that caller may do for this task.

The current reference workflow uses synthetic support tickets, scripted proposals, and separately authenticated development roles using HMAC keys. An operator assigns a bounded task, the primary delegates read-only access to a child, and the gateway checks every protected action. Updates require exact operator approval. Parent pause or revocation prevents subsequent child actions. Evidence and lineage record the outcome.

Start with [the reviewer guide](REVIEW_GUIDE.md), [architecture](ARCHITECTURE.md), and [current limitations](LIMITATIONS.md). The pilot needs no paid model or cloud credentials.

The workspace console, procurement lab, and optional model/AWS examples are legacy evaluation paths with different boundaries. They remain available but are not the primary public-review workflow.
