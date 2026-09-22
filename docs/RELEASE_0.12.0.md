# v0.12.0 review release

The v0.11.0 durable gateway could reuse an approved request ID under a different task and could dispatch the same ID concurrently. This release binds each request to immutable canonical content and atomically reserves it before execution. It retains pending input for operator review and exposes durable execution-claim states.

The root folder listing example now passes resource validation. Delegation evaluation checks ancestor grants. Event-chain appends are serialized. The SDK serializes calls within one gateway instance.

## Behavior and failure contract

A mismatched canonical request is denied without altering the original approved operation. A concurrent call receives REQUEST_IN_PROGRESS. A completed or uncertain execution cannot be dispatched again under the same ID. If execution or result persistence fails, state becomes unknown when storage permits; abrupt process death may leave evaluating. Neither is automatically retried. The operator must reconcile the actual tool effect before creating a replacement request.

Authorization is rechecked when a pending request resumes. Approval cannot expand permission. Approve/reject decisions are terminal. Task/grant checks limit approval lifetime; separate approval expiration remains future work.

## Scope

No REST/MCP connector, remote authentication, production secret store, isolated deployment, or automatic recovery was added. Docker remains the existing offline-tour configuration. This release is intended for independent local technical review, not sensitive production use.

See VALIDATION.md for performed checks and LIMITATIONS.md for trust boundaries.
