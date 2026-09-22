> Legacy evaluation paths. For the current authenticated ticket pilot, use [the reviewer guide](REVIEW_GUIDE.md), [architecture](ARCHITECTURE.md), and [capability matrix](CAPABILITIES.md). The descriptions below apply only to the older workspace/laboratory examples.

# Integration guide

## Connector contract in v0.7

A connector registers a unique `connector_name`, a namespaced `tool_name`, a non-empty `supported_actions` set, `health()`, and `execute(action, resource)`. `ConnectorRegistry` rejects duplicate names and invalid contracts. Registration is discovery and validation only: every execution must still pass through the lifecycle gateway.

Run `scopedact connectors` to inspect bundled contracts. The AWS IAM read-only connector is the only external implementation shipped in v0.7.

## Boundary

An integration implements one small interface: a protected tool exposes a
stable `tool_name` and an `execute(action, resource)` method. The gateway checks
task lifecycle state, durable replay state, the request's tool binding, task
grant, and configured approval before invoking that method.

The integration must still enforce its own native authentication and
authorization. ScopedAct is an additional application-layer decision point; it
does not replace cloud IAM, API authorization, network controls, or service-side
validation.

## Model adapters

A model adapter is an untrusted proposer. Its output is parsed through the exact
`ActionRequest` schema. Unknown fields, missing fields, malformed identifiers,
ungranted actions, ungranted resources, and mismatched tools are rejected.

Do not put secrets, credentials, confidential records, or customer data in model
prompts. The included live adapter is optional and not exercised by the
deterministic test suite.

## AWS IAM example

`AwsIamReadOnlyTool` is intentionally narrow. It constructs an argument list
without a shell and accepts only:

- action: `get_role`
- resource: `iam-role:<valid-role-name>`
- AWS operation: `aws iam get-role`

Use a dedicated sandbox profile with an IAM policy restricted to the exact demo
role. Native AWS IAM remains the final backstop if the application is bypassed.

## Adding a connector

1. Give the connector an immutable namespaced `tool_name`.
2. Validate an allowlist of actions and resource formats.
3. Avoid invoking a shell or concatenating commands.
4. Return only the fields required by the workflow.
5. Add deterministic tests with mocked external I/O.
6. Document required native permissions and safe test isolation.
7. Route lifecycle integrations through `LifecycleGateway`; never expose the connector directly
   to an agent runtime.
8. Connect grant issuance to a trustworthy upstream authority source and
   authenticate both initiators and reviewers in any real deployment.
