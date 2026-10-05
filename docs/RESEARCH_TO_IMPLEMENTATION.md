# Research behind the design

ScopedAct applies a bounded subset of ideas explored in Jay Goradia's writing.
This mapping describes design influences, not publisher endorsement, proof of
novelty, or evidence of independent adoption. Verify publication status and public
links before adding publisher badges; draft PDFs are not bundled in this repository.

| Work | Design connection | Implementation / evaluation | Boundary |
|---|---|---|---|
| The Identity Fabric: Securing Delegation in Multi-Agent AI Systems | Narrow authority and preserve delegation lineage | Parent/child grants, expiry, ancestor intervention; live lab diagnostic child | No hardware attestation or federated workload identity |
| When Systems Act for Users (ACM Interactions, DOI 10.1145/3829213) | Make actors, permissions, activity and intervention understandable | Task overview, scope, resource map, exact proposal review, verification state | No universal undo; map covers gateway requests only |
| The New CTI Blind Spot: AI Agents and Non-Human Identities | Relate actions to their task and authority | Attribution, explicit denials, metadata export and deliberate misuse probes | A scope violation is not a semantic-intent classifier |
| Your API Authentication Isn't Broken; It's Quietly Failing in These 6 Ways | Separate authentication and authorization; validate tokens and internal requests | Signed expiring lab tokens, authenticated service calls, server-side task checks | Shared HMAC development secrets, not an enterprise identity service |
| The Governance Gap Between AI Pilots and Production | Ownership, exception handling and operational evidence | Operator approval/intervention, timeout reconciliation, fresh recovery check | Single-process local evaluation, not production certification |

The [live lab](LIVE_INCIDENT_LAB.md) offers a reproducible place to examine these
ideas. The strongest next feedback is whether an independent engineer can use and
understand the controls in their own evaluation, including their failed attempts.
