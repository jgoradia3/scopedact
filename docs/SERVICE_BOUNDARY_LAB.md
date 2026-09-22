# Service-boundary lab

## Components

`scopedact lab` starts three independently addressed localhost HTTP servers:

| Component | Default address | Trust boundary |
| --- | --- | --- |
| Operator console | `127.0.0.1:8765` | Human lifecycle and approval controls |
| ScopedAct gateway | `127.0.0.1:8770` | Client authentication, authorization and audit |
| Synthetic invoice tool | `127.0.0.1:8780` | Accepts only the runtime gateway credential |

`scopedact lab-agent` is a separate process. It signs every request over the method, path, timestamp, nonce, and SHA-256 body digest. The gateway validates the signature, binds the client identifier to the configured task actor, enforces a 60-second clock window, and persists each nonce before processing the request.

The gateway then applies normal lifecycle checks. Only an allowed request reaches the protected tool. The internal gateway-to-tool credential is randomly generated when the lab starts and is not available to the agent client.

## Manual approval sequence

The client stops after payment returns `APPROVAL_REQUIRED`. Approve the pending request in the console, then copy the printed resume command. Resubmission uses a new API nonce but the same lifecycle request ID, allowing the gateway to associate it with the approval.

## Security boundaries

The lab demonstrates protocol separation and enforceable request paths, but all servers still run as threads in one local Python process for convenient startup. Port separation is not OS process isolation. The development client key is public, the console has no user login, HTTP has no TLS, and the tool is synthetic. Production deployment would require separate processes or workloads, managed client identity, TLS/mTLS, protected secrets, authenticated operators, network policy, rate limits, and operational hardening.
