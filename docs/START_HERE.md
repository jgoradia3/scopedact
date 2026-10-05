# Give agents a task—not unrestricted access.

**New reviewers: [start here](REVIEWER_QUICKSTART.md).** One command starts the lab
and opens a private sign-in link. No operator-key upload is needed.

Start the new [live incident-response lab](LIVE_INCIDENT_LAB.md) to investigate and
repair a running authentication service. See [validation results](LIVE_LAB_VALIDATION.md),
including failed model runs and unverified areas. Earlier evaluations remain below.

For a security-engineer evaluation, start with [STG-AUTH-204: staging authentication regression](INCIDENT_EVALUATION.md). It contains the incident briefing, reproducible commands, access boundaries, and expected outcomes.


The v0.15.0 managed workspace adds an interactive task-authority map and operator controls.
See [Workspace guide](WORKSPACE.md) for its workflow, architecture boundary, setup, and limitations.
The ticket-pilot material below remains applicable to that separate workflow.

ScopedAct checks an agent's tool requests before they execute. It helps demonstrate a simple rule: access should fit the assignment, even when an agent delegates work to a helper.

Imagine asking an agent to investigate support ticket T-100. It can read that ticket, delegate a read-only task, and propose a comment. ScopedAct blocks access outside the grant, holds sensitive updates for exact operator approval, and records the action chain. Revoking the parent prevents subsequent child actions.

## Choose your starting point

- **Understand the behavior:** see the [illustrated walkthrough](../README.md#see-it-in-action).
- **Run the demonstration:** follow the [local setup](../README.md#try-it-locally).
- **Evaluate a control:** use the [reviewer guide](REVIEW_GUIDE.md).
- **Inspect the design:** read [architecture](ARCHITECTURE.md), [capabilities](CAPABILITIES.md), and [validation](VALIDATION_0.14.1.md).

The original ticket pilot (v0.14.1) is a developer preview for controlled evaluation with synthetic data. It uses real HTTP calls, scripted proposals, and separate HMAC development-role keys. No paid model or cloud credentials are needed. See [limitations](LIMITATIONS.md).

The workspace console, procurement lab, and optional model/AWS examples are legacy evaluation paths with different boundaries. They remain available but are not the primary review workflow.
