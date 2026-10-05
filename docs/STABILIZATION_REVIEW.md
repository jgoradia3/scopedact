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
