# Control-to-test map

| Control | Regression evidence |
|---|---|
| Canonical approval binding | test_review_hardening: every canonical field, pending substitution; test_v011_application: signed cross-task substitution |
| At-most-one dispatch per durable request ID | Concurrent callers in test_review_hardening |
| Unknown effect is not retried | Side-effect-then-timeout and restart claim tests |
| Pre-dispatch durable evidence | Dispatch-evidence failure blocks tool test |
| Human-readable approval | Escaped exact-input dashboard test |
| Root-folder resource | Signed HTTP folder:. test in test_v011_application |
| Descendant authority | Ancestor revocation and missing-parent tests |
| Workspace boundary | Traversal and actual internal symlink tests |
| Approved child after parent intervention | test_pilot_delegation: pause and revoke after approval deny dispatch, preserve ticket state, and leave no mutation receipt |
| SQLite connection ownership | tools/check_sqlite_resources.py tracks every in-process SQLite connection across the test suite |
| Guided incident policy and runner | [Assignment tests](../tests/test_incident_assignment.py), [reviewer tests](../tests/test_reviewer.py), [agent tests](../tests/test_agent.py) |
| Native startup and restart | [Native integration tests](../tests/test_native_review.py) |
| Console interactions | [JavaScript regressions](../tests/test_console_actions.cjs) |
| Current run results | [Dated validation](STABILIZATION_REVIEW.md); rerun the complete suite for the commit under review |

These are fixture-specific correctness tests. They do not estimate real-world attack-blocking rates, prove arbitrary-model safety, or replace independent review. Hosted CI and platform compatibility should be assessed separately from local validation.
