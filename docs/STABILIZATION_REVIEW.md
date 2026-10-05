# Stabilization review

This branch brings the local incident lab and reviewer console into public review. It is not a production release or evidence of independent adoption.

## Scope

ScopedAct demonstrates task-scoped authority, independent runtime enforcement, bounded delegation, attribution, approval, and revocation. The staging login incident is a test environment for these controls, not the product's purpose. Role selection simulates permission profiles under the authenticated local operator; enterprise identity integration is not implemented. Explicit policy enforces authorized scope, not arbitrary natural-language intent.

## Denial intervention

The guided model runner pauses on a confirmed PERMISSION_NOT_GRANTED response before another queued tool call can execute. Remaining calls from that model response are discarded. The private journal retains the completed results and observed versions. Only the operator can choose Continue with permitted evidence. Continuation uses the same task and permissions, rechecks authorization at the gateway, and asks the model for its next action. Expiration and revocation still apply. End this evaluation revokes remaining task authority.

This is a runner pause, not an automatic gateway-wide suspension: another independently running client using the task could still attempt permitted actions. Use Stop access or End to revoke task authority. Uncertain requests are not treated as confirmed denials and cannot use this continuation path.

## Validation gates

Automated suite, SQLite ownership checks, console interaction regressions, hosted CI, and fresh local-model evaluations are required before tagging a release. Live model results must be reported separately from deterministic model doubles. No release is implied by this branch.

The earlier intern run ended with rejected_model_tool after four requests. Its journal did not retain enough detail to distinguish an unsupported tool from invalid arguments or a proposal without a successful preceding read. The runner now records a safe error category and the console explains that the invalid call was not dispatched. It does not guess or rewrite invalid calls.

## Delegation check

Run `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_workspace.py'` and the ticket-pilot delegation evaluation described in `docs/REVIEW_GUIDE.md`. The suite covers bounded child permissions and ancestor intervention; the Docker evaluation also demonstrates a child read denied after parent revocation. These are maintainer-controlled tests, not independent use.

## Publication boundary

Only source, tests, documentation, static assets and synthetic examples belong in the review branch. Exclude `.scopedact*`, key files, databases, model journals, build output, and local evaluation directories. Do not upload runtime credentials. Historical evaluation documents are explicitly maintainer-run and do not establish adoption.

## Latest validation (2026-10-05)

- 184 automated tests passed; 2,825 SQLite connections opened and none unclosed.
- Console regression checks, wheel and source builds passed. Package archives excluded runtime data and secrets.
- Fresh intern run: two allowed reads, configuration denied, runner paused with one queued call discarded. Operator continuation kept the task unchanged; the model finished without additional requests.
- Fresh responder run: four reads succeeded, but the model misinterpreted configuration evidence and did not propose a repair. No successful repair or recovery is claimed for this run.
- Initial hosted Docker jobs failed. A Linux private bind-mount ownership problem was reproduced in a Linux container; matching the host UID reads private files without extra capabilities. Compose/launcher/CI fixes are pending hosted revalidation.

Keep this branch in draft review. Do not tag a release until hosted CI passes and the model reliability limitation is addressed or clearly bounded in the reviewer exercise. Evidence: [local evaluation](evaluations/stabilization-2026-10-05.json).

## Native reviewer package — October 5, 2026

Added a Docker-free, loopback-only launcher using the existing services, gateway,
console and Ollama agent. Fresh wheel installation and console sign-in were checked
on macOS/Python 3.11. A real qwen3:1.7b run completed two permitted diagnostic reads,
then attempted configuration access and paused after a real permission denial.
The evaluation was then ended. [Sanitized run record](evaluations/native-2026-10-05.json).
This did not validate a successful native repair or independent adoption.

Apple GPU initialization failed in the automated execution environment. The verified
run used CPU inference, with `LLAMA_ARG_DEVICE=none` on the Ollama 0.35.0 server and
`--cpu` on the launcher. Windows native execution is not supported; use the Docker setup there.
Native mode deliberately does not claim container/network or same-user isolation.

The native integration regression uses a fake model to exercise live local HTTP
services, denial/pause, directory locking and restart preservation. It is separate
from the recorded live-model evaluation. The full suite passes 185 tests.

A [narrated video](DEMO_VIDEO.md) uses saved Docker-lab screenshots, with clear
edited-recording and synthetic-voice disclosure. Source and media contain no local
keys, databases, or private agent journals.
