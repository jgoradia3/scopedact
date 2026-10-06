> Historical validation snapshot. Results and publication status below apply to that recorded run. See [the latest review record](STABILIZATION_REVIEW.md) for subsequent checks.

# Local agent evaluation — 0.16.0

On October 2, 2026, the maintainer ran Ollama 0.35.0 with qwen3:1.7b
(model ID prefix `8f68893c685c`) locally in Docker. No cloud model account was used.
All documents were synthetic. This is internal testing, not external adoption.

## Observed live behavior

1. The model chose two document reads, which executed through the signed gateway.
2. In an early run it falsely claimed an update without issuing an update tool call.
   No update executed. Runner output now labels model prose as unverified and reports
   confirmed update counts separately.
3. In another run it guessed a document version. That proposal stayed held and was
   rejected. The runner now binds proposals to versions returned by successful reads;
   the model cannot supply version numbers.
4. With that change, the model read the incident runbook and diagnostic notes,
   generated a replacement, and called `propose_update`. ScopedAct held the proposal.
5. An **automated test operator**, not a human reviewer, approved the exact synthetic
   proposal. The installed wheel's CLI retried it and executed the update to version 2.
   The task map records the request as `succeeded`.
6. A separate live request for an unassigned document returned
   `PERMISSION_NOT_GRANTED`; no read executed and the runner stopped.

The model's proposed wording still needs editorial review. For example, it suggested
reviewing sessions “marked as stale,” although the fixture established stale sessions
without establishing such a marker. Runtime authorization does not establish factual
accuracy or guarantee a useful answer.

[Machine-readable evaluation metadata](evaluations/local-agent-0.16.0.json) includes
request IDs and actual decisions. Its task counts include both the initial rejected
proposal and the final run. It omits keys, prompt bodies, and document text.

## Automated and packaging checks

- Full resource-checked suite: 142 tests; zero unclosed SQLite connections.
- Runner tests use deterministic model doubles against the real HTTP gateway. They
  cover exact retry, approval plus revocation, denial, tool restrictions, budgets,
  uncertain dispatch, model failure, unverified claims, and observed-version binding.
- Source distribution and wheel build; installed `scopedact-agent` and operator
  `create-task` commands verified. Workspace web assets remain in the wheel.
- Hosted GitHub CI has not run on this unpublished source state.

## Limits

One primary model-driven agent is integrated. The helper/delegation demonstration
remains scripted. The map shows gateway-covered document requests, not model thinking,
all host activity, or every API an arbitrary agent might access. Native execution is
not an OS sandbox. See [setup and boundaries](LOCAL_AGENT.md).
