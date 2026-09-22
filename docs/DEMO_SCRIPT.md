> Legacy workspace/laboratory guide. Current ticket-pilot controls and trust boundaries are described in [pilot security](PILOT_SECURITY.md) and [the reviewer guide](REVIEW_GUIDE.md).

# Ten-minute reviewer demonstration

## Purpose

Show that an external agent cannot directly decide or execute sensitive tool actions.

## Script

1. Run `scopedact tour` and establish the three terms: proposal, decision, execution.
2. Start `scopedact lab` and point out the three localhost addresses.
3. Run `scopedact lab-agent` in a second terminal.
4. Observe three `PERMISSION_GRANTED` decisions with `TOOL EXECUTED: YES`.
5. Observe payment return `APPROVAL_REQUIRED` with `TOOL EXECUTED: NO`.
6. Open the console and identify the active task, exact grant, pending approval, and event timeline.
7. Approve the payment and run the printed resume command.
8. Observe `PERMISSION_GRANTED` and `TOOL EXECUTED: YES` for the same lifecycle request.
9. Close the task and explain that the grant is revoked.
10. State the boundary: the controls are real; the business data, payment, identities, and deployment are synthetic/local.

## Feedback questions

- Was the problem understandable before installation?
- Was the difference between API receipt, authorization, and execution clear?
- Which control would be necessary before connecting a real internal tool?
- Which evidence would a security reviewer or auditor need?
- Where did setup or terminology create friction?
