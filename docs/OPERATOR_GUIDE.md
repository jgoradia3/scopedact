> Legacy workspace/laboratory guide. Current ticket-pilot controls and trust boundaries are described in [pilot security](PILOT_SECURITY.md) and [the reviewer guide](REVIEW_GUIDE.md).

# Operator guide

ScopedAct `v0.11.0` includes a local hands-on workflow for inspecting and
changing task lifecycle state. It is a demonstration, not an authenticated
administrative console.

## Use an isolated database

Every lifecycle command accepts `--database`. Use a separate file for each
evaluation when you do not want histories mixed together:

```bash
scopedact init-demo --database audit/operator.db
```

Pass the same database to later commands.

## Inspect state

Machine-readable JSON:

```bash
scopedact status --database audit/operator.db
```

Local dashboard:

```bash
scopedact dashboard --database audit/operator.db
```

The server accepts loopback addresses only. The demonstration has no user
authentication, administrative authorization, TLS, or production hardening.

## Task controls

```bash
scopedact task pause  TASK_ID --database audit/operator.db
scopedact task resume TASK_ID --database audit/operator.db
scopedact task revoke TASK_ID --database audit/operator.db
scopedact task close  TASK_ID --database audit/operator.db
```

- `pause` temporarily blocks new actions.
- `resume` is allowed only from `paused`.
- `revoke` is terminal and marks the underlying task grant revoked.
- `close` is terminal and marks the underlying task grant revoked.

This release does not implement recovery from a revoked or closed task. Create a
new task instead.

## Approval controls

When `approve_payment` is proposed, the gateway returns `APPROVAL_REQUIRED` and
prints the request ID. Decide it with:

```bash
scopedact approval approve REQUEST_ID \
  --reviewer human:reviewer --database audit/operator.db
```

or:

```bash
scopedact approval reject REQUEST_ID \
  --reviewer human:reviewer --database audit/operator.db
```

An approved request must be submitted again with the same request ID. A
rejected request is terminal; a later reuse is rejected as a replay.

The reviewer name is an unauthenticated demonstration identifier. It does not
prove who made the decision.

## State protection

SQLite and JSONL files are local evidence for demonstration and troubleshooting.
They are not protected from a user with filesystem access and are not
protected from a privileged local user. Lifecycle events have a basic SHA-256 hash chain; verify it with `scopedact verify-events`. This is not a signature or immutable log. Do not store secrets or sensitive records in these files.
