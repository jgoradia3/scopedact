# Give agents a task—not unrestricted access.

ScopedAct checks an agent's tool requests before they execute. It helps demonstrate a simple rule: access should fit the assignment, even when an agent delegates work to a helper.

Imagine asking an agent to investigate support ticket T-100. It can read that ticket, delegate a read-only task, and propose a comment. ScopedAct blocks access outside the grant, holds sensitive updates for exact operator approval, and records the action chain. Revoking the parent prevents subsequent child actions.

## Choose your starting point

- **Understand the behavior:** see the [illustrated walkthrough](../README.md#see-it-in-action).
- **Run the demonstration:** follow the [local setup](../README.md#try-it-locally).
- **Evaluate a control:** use the [reviewer guide](REVIEW_GUIDE.md).
- **Inspect the design:** read [architecture](ARCHITECTURE.md), [capabilities](CAPABILITIES.md), and [validation](VALIDATION_0.14.1.md).

The current package, v0.14.1, is a developer preview for controlled evaluation with synthetic data. It uses real HTTP calls, scripted proposals, and separate HMAC development-role keys. No paid model or cloud credentials are needed. See [limitations](LIMITATIONS.md).

The workspace console, procurement lab, and optional model/AWS examples are legacy evaluation paths with different boundaries. They remain available but are not the primary review workflow.
