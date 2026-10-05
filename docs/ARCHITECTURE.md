# Current architecture — v0.14.1

## Guided reviewer access (0.20.0)

The trusted host launcher generates a one-time sign-in code; only its hash and
expiry enter the gateway state directory. A same-origin exchange establishes an
HttpOnly local operator session. The operator HMAC key never enters the browser.
Signed agent clients remain separate and cannot use operator-only guided routes.

The gateway coordinates fixed scenario setup and worker APIs. The scenario service
can introduce only the declared local fault. The worker runs on the model network
with the agent credential and a control credential, without backend keys or a Docker
socket. Model requests still traverse the authorization gateway. Human approval and
execution remain distinct actions, and recovery requires a fresh login check.

Sessions and worker execution ownership are single-process local state. Gateway
restart expires sessions. Worker restart marks an in-flight operation interrupted;
it does not silently replay it. See [reviewer setup](REVIEWER_QUICKSTART.md).

## Live incident lab (0.19.0)

The live lab reuses task grants, approvals, lifecycle controls and the resource map.
An isolated Ollama client sends signed requests to the gateway, which calls a fixed
operations API. That API reaches the portal authentication service, which validates
tokens issued by a separate synthetic identity service. Portal configuration,
deployment history and mutation receipts are stored transactionally. Login checks
produce fresh runtime events and separate gateway verification evidence.

The gateway has an operations credential; the operations service has a portal
credential; the agent has neither. Docker networks separate the agent/model,
gateway-to-operations, operations-to-portal and portal-to-identity boundaries.
Only the gateway is published on host loopback. The host/Docker administrator is
trusted. The separately initiated child receives only log-read authority.

The versioned document API is reused as a resource representation: `doc:` names
and `read_document` calls in this lab refer to live service snapshots. No imported
fixture is used to establish login failure or recovery. Details and limitations
are in [the live lab guide](LIVE_INCIDENT_LAB.md). Earlier architectures follow.

The v0.15.0 managed workspace adds an interactive task-authority map and operator controls.
See [Workspace guide](WORKSPACE.md) for its workflow, architecture boundary, setup, and limitations.
The ticket-pilot material below remains applicable to that separate workflow.

The primary reference workflow is the authenticated synthetic ticket pilot. It separates the operator, primary agent, diagnostic child, authorization gateway, and protected ticket service. Separately authenticated development roles use HMAC keys; identity assurance is limited to possession of those configured secrets.

```mermaid
flowchart TD
    O[Operator: own HMAC key] --> R[Root task authority]
    P[Primary agent: own HMAC key] --> D[Request bounded child grant]
    R --> D
    D --> C[Diagnostic child: own HMAC key]
    P --> G[ScopedAct gateway]
    C --> G
    R --> G
    O --> A[Exact approval and lifecycle controls]
    A --> G
    G --> T[Fixed-route ticket REST connector]
    T --> S[Protected synthetic ticket service]
    G --> E[Persistent decisions and lineage]
    S --> I[Persistent ticket versions and receipts]
```

## Request and authority flow

1. The operator issues a 15-minute root task with exact read/update permission pairs for one ticket.
2. The primary may request a child grant from its own active root task. The gateway enforces a nonempty permission subset, preserved initiator, and expiry no later than the parent's. Child grant, lifecycle task, and issuance event commit atomically.
3. Signed requests authenticate method, path, body, timestamp, and nonce. API roles restrict issuance, review, intervention, and evidence access. Parent labels come from stored grants, not action callers.
4. Durable execution claims bind each request ID to its canonical proposal. Before dispatch, task, actor, tool, grant bounds, expiration, revocation, and ancestor lifecycle checks must pass.
5. An update additionally requires operator approval of that exact proposal digest within the approval TTL. Resuming an approved request rechecks authority; approval does not override subsequent parent pause or revocation.
6. The connector calls only supported ticket routes. The backend checks its own credential, expected ticket version, and idempotency key. Ambiguous effects require operator reconciliation; the gateway does not automatically retry them.
7. Stored grants and attributed action events supply the operator-only lineage report. Local chained events and backend receipts provide review evidence within the stated trust boundary.

## Deployment and ownership

The gateway joins front and protected Docker networks. The ticket service joins only the protected internal network and publishes no host port. Primary and child probes join only the front network and each receive only their own key. The trusted evaluator holds several role keys to drive deterministic scenarios; it is not an untrusted agent runtime.

The gateway is published at loopback port 8870. Startup prepares secret files and state, then drops to UID/GID 10001. SQLite databases live on named volumes. Each database owner explicitly closes its connection; transaction context managers alone do not close SQLite connections.

One gateway process serializes synchronous invocation and intervention. Acknowledged revocation prevents subsequent protected dispatch; in-flight calls are not canceled or undone. See [limitations](LIMITATIONS.md), [connector contract](CONNECTOR_DEVELOPMENT.md), and [delegation](DELEGATION.md).

## Legacy evaluation paths

The workspace application, unauthenticated operator console, procurement lab, process-local SDK, and optional model/AWS examples remain separate evaluation paths. Their protections differ from the ticket pilot and do not inherit its deployment boundaries. See [application guide](APPLICATION_GUIDE.md), [SDK integration](SDK_INTEGRATION.md), and the legacy section in [limitations](LIMITATIONS.md).
