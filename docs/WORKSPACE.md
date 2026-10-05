# Investigate an agent task in a managed workspace

ScopedAct's workspace console connects a task's explicit permissions to agent activity,
delegation, approvals, and execution results. It runs locally without an external account
or a paid model. The included client is scripted: it exercises real authenticated HTTP
requests, not model reasoning. Your own client can use the same API.

## Install and start

From the repository root, using Python 3.10 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
scopedact-workspace init
scopedact-workspace serve
```

Open http://127.0.0.1:8890. Select `.scopedact-workspace/secrets/operator.key`
in the login screen. It is read locally into browser memory to sign requests and is not
uploaded as a document or stored in localStorage. Lock or reload clears the login.
Treat this operator key as an administrator credential; never give it to an agent.

The managed workspace contains imported copies of text documents in a SQLite store.
It is not a live mount of your documents folder. Local processes running as your OS user
can still access that store; use the container boundary below for an untrusted agent.

## Run the investigation

In a second terminal with the same virtual environment:

```sh
scopedact-workspace demo --reads 101
```

Refresh the console. The example creates a 15-minute assignment, delegates read access
for five minutes, reads the assigned documents, attempts an unassigned read, and proposes
an exact replacement of the runbook. The console should show **104 attempts: 102 completed,
1 blocked, and 1 held**. The repeated reads collapse into one resource branch.

1. Expand the helper's blocked resource. Inspect its request ID and `PERMISSION_NOT_GRANTED` decision.
2. Inspect **Granted scope** on the primary and helper. Helpers cannot expand the parent's permissions or lifetime.
3. Open **Review proposal**. Compare current content with the proposed replacement. Approve or reject.
4. To execute an approved proposal, run:

```sh
scopedact-workspace resume-demo
```

Refresh. Approval itself does not execute anything. The same request is rechecked at dispatch.
A changed document version requires a new proposal. Repeating a completed request is blocked.

5. Pause the task in the console and run `scopedact-workspace probe-demo`. A child action
   is blocked while its ancestor is paused. Resume restores access only while grants remain valid.
6. Revoke the parent and probe again. Subsequent child requests remain blocked.
7. Inspect **Evidence timeline**, filter by resource or request ID, then **Export metadata**.
   Export includes the complete returned task map, without document bodies. Resource names,
   actor identifiers, timestamps, and authority remain visible.

If the helper expires during review, rerun the demo to create a fresh assignment. The
console reports effective inactivity through expiration or ancestor controls.

## Import your own test documents

```sh
scopedact-workspace import /absolute/path/to/notes.md --name team-notes.md
```

Import is a trusted operator operation. Use UTF-8 text, at most 8000 bytes. Existing names
are not overwritten. Identifiers such as `doc:team-notes.md` never resolve to filesystem
paths. Path traversal, absolute paths and slash-containing names are rejected.

In **Create assignment**, enter a non-sensitive summary and select the exact read/update
permissions. The summary is descriptive; the configured permissions enforce scope.
Copy the task ID into your agent integration. The example below performs a real read with
only the primary agent key:

```python
from pathlib import Path
from uuid import uuid4
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT

client = Client("http://127.0.0.1:8890", AGENT,
                Path("/run/agent.key").read_text().strip())
status, result = client.post("/v1/actions", {
    "task_id": "COPY_OPERATOR_CREATED_TASK_ID",
    "request_id": "request:" + uuid4().hex,
    "action": "read",
    "resource": "doc:team-notes.md",
})
print(status, result)
```

An update uses `action: update` and `input: {text: <complete replacement>, expected_version: <read version>}`.
Keep its entire body and request ID for the post-approval retry. Never mint a different
request automatically after an uncertain execution. Operators use reconciliation first.

The API retains the historical development role identifiers `agent:ticket-pilot`,
`agent:diagnostic`, and `human:pilot-operator`; these are HMAC-key roles, not enterprise identities.
One level of delegation is supported. See [delegation](DELEGATION.md) for the route contract,
using `doc:` resources in this workspace.

## Recover a prior document version

Every successful replacement retains prior versions. Export is an operator CLI operation:

```sh
scopedact-workspace export-document --resource doc:runbook.md
scopedact-workspace export-document --resource doc:runbook.md --version 1 > recovered-runbook.md
```

This recovers a copy. It does not silently roll back current content or invalidate audit history.
To restore current content, submit the old text as a new, approved replacement against the current version.

## Container evaluation boundary

Stop the local `serve` process before using the same port. Initialize state first, as above:

```sh
docker compose -f compose.workspace.yaml up --build -d --wait
docker compose -f compose.workspace.yaml run --rm agent-probe
docker compose -f compose.workspace.yaml run --rm child-probe
```

Only the gateway mounts the managed documents and all role keys. Each probe mounts its own
key, lacks the state volume and Docker socket, and verifies operator endpoints are denied.
The agent network is internal. The gateway also joins a console network so Docker can publish
the console/API on host loopback. Place your own
agent in an equivalent container with only its key. The example does not provision a live
model or prove isolation for other deployments. The operator-run demo holds all role keys
and is a trusted test harness, not that isolated agent.

```sh
docker compose -f compose.workspace.yaml down
```

State persists in the ignored `.scopedact-workspace` directory. Do not commit or publish it.

## Evidence semantics and limits

- **Attempts** count calls, including holds and retries, not distinct business operations.
- **Completed** means the connector returned successfully and the gateway recorded it.
- **Held** is an approval-required attempt; it remains historical after later approval.
- **Blocked** includes permission denials, replay prevention, and lifecycle denials. It is
  not an automatic assertion of malicious behavior.
- **Uncertain** means execution raised an error. Current gateway handling is deliberately
  conservative, including definite document-version conflicts in this bucket. Inspect the
  connector failure category and use receipt reconciliation. No receipt alone does not prove
  non-execution for a potentially in-flight operation.
- Mutation, version history, and backend receipt commit in one document-store transaction.
  Gateway evidence is a separate transaction. Reconciliation can bridge a crash after commit.
- Pause/revoke serialize with dispatch in one gateway process. They do not abort operations
  already running or undo completed changes. Multi-process gateway operation is unsupported.
- This maps authenticated gateway activity only. Authentication errors, invalid input rejected
  before routing, arbitrary shell/network activity, and bypasses are not attributed task events.
- Local event-chain verification detects changes only relative to retained local state; an
  administrator able to rewrite the entire database can rebuild it. It is not independent attestation.
- Document bodies, version history, and proposals are plaintext locally. Export metadata can
  still be sensitive. No enterprise SSO, multi-user tenancy, key rotation UI, retention scheduler,
  SIEM ingestion, MCP adapter, automatic anomaly detection, or universal API discovery is implemented.
- The map loads task history in memory. Large histories can exceed the 2 MiB client response
  limit; 101 repeated reads are tested, not unlimited event volumes. Refresh is manual.
- The gateway and operator host are trusted. The browser login is for local evaluation, with
  restrictive CSP, fixed asset routes, Host/Origin checks and no CORS access. Do not expose it publicly.

## Independent review

Record the version, OS, installation steps, selected workflow, observed outcomes, failures,
and whether you used scripted clients or your own agent. A useful review answers whether
you could identify the blocked resource, explain the helper's authority, and reconstruct
an approved change without reading every raw event. Report actual experience in your own
words. Testing is not production adoption. See [review guide](REVIEW_GUIDE.md).

## Linux bind-mount ownership

Before manual Docker Compose commands on Linux, set `export SCOPEDACT_UID=$(id -u) SCOPEDACT_GID=$(id -g)` in the shell that initialized the state directory. Containers then run as the owner of the private state and key files while retaining `cap_drop: ALL`. Do not make secrets world-readable. The reviewer launcher sets these values automatically on Linux. Docker Desktop retains its existing default.
