# v0.14.0 — Bounded delegation and review clarity

This release addresses the shared review gap in v0.13: the authenticated ticket pilot now demonstrates primary-agent to child-agent delegation and attributable tool calls. It preserves the ticket workflow, exact approvals, idempotency, recovery, and isolated deployment.

## Changes

- Add a separately keyed diagnostic child role and a primary-only delegation endpoint.
- Enforce one-parent subset permissions, inherited initiator, bounded expiry, and one exposed delegation hop.
- Commit child grant, lifecycle record, and issuance evidence atomically.
- Recheck ancestor pause/revocation/expiry on child actions.
- Record authenticated actor, grant actor, parent, parent task, delegation ID, tool, decision, and outcome in attributed events.
- Add operator-only JSON and readable lineage reports and a 19-check delegated evaluation.
- Run isolation probes for both primary and child containers, each with only its own key.
- Add VISION.md, a capability matrix, architecture diagram, and one focused reviewer guide.

## Feedback disposition

| Feedback | Disposition |
|---|---|
| Visible bounded delegation | Implemented in the main ticket pilot |
| End-to-end delegated lineage | Implemented from authenticated requests and stored grants |
| Precise revocation language | Documentation states that subsequent protected actions are denied; no in-flight cancellation claim |
| Provider-neutral project vision | Added; ticket service described as one reference workflow |
| Capability status and legacy boundaries | Explicit tables and current reviewer guide |
| Precise REST/isolation/persistence claims | Limited to fixed-route connector and tested container/restart behavior |
| Public CI and release visibility | Updated workflow included; publication and hosted execution not performed here |
| MCP/live model, OIDC, task context, policy binding | Explicit future milestones, not represented as complete |
| Advanced graph/SOR/research mechanisms | Deliberately excluded from this bounded public milestone |

The reviews differed on which larger future integration should come next. This release implements their overlapping near-term recommendations without claiming an enterprise platform. No reviewer endorsement or independent validation of v0.14 is implied.
