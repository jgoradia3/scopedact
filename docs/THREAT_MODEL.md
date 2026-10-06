# Threat model

ScopedAct protects configured tool calls that pass through its gateway. The current
reviewer workflow is a live-model investigation of a synthetic staging incident.
It is a controlled evaluation, not a security boundary around every process on a laptop.

## Assets and trust

Protected assets are task grants, approval records, service configuration, backend
credentials and execution evidence. The model's instructions and retrieved content
are untrusted proposals; they cannot issue grants or approve their own changes.

The host administrator, gateway, policy configuration, trusted launcher, operator
and supplied service implementations are trusted. The reviewer worker orchestrates
model calls using constrained tools. Its control credential is privileged; it must
not be exposed as a model tool. Enterprise identity federation is not implemented.

## Threats and controls

| Threat | Boundary enforced | Important limit |
|---|---|---|
| Agent requests unrelated access | Exact task action/resource grant checked before dispatch | A permitted action can still be inappropriate; intent is not inferred from prose |
| Retrieved content redirects the model | The redirected tool request faces the same independent checks | No universal prompt-injection detector; misleading allowed output remains possible |
| Agent expands delegated authority | Child permissions and expiry constrained by parent; later calls recheck ancestry | One exposed delegation hop in the ticket pilot, no multi-parent analysis |
| Approved input is substituted | Canonical request binding and exact proposal approval | Approval does not prove the proposed repair is correct |
| Signed request is replayed or duplicated | Nonce checks, durable execution claims and backend receipts | A different request ID is a different operation; uncertain effects require reconciliation |
| Access is revoked after approval | Authority is checked again before later dispatch | In-flight work is not canceled or undone; no distributed revocation |
| Remote caller reaches the local console | Loopback publishing, short-lived sign-in, session/CSRF and origin/host checks | Do not expose the local deployment publicly; HTTP signing is not encryption |
| Agent bypasses the gateway | Supplied Docker networks and separate service credentials | Native services share the same OS account; native mode is not a sandbox |
| Reviewer misreads execution history | Task/request attribution, decisions, receipts and activity map | Only gateway-covered activity; not model reasoning or host-wide monitoring |
| Privileged operator rewrites evidence | Local hash chaining supports consistency checks | Not immutable, externally notarized or administrator-proof evidence |

## Deployment distinctions

- **Native incident review:** loopback services and authenticated requests, all under
  the user's OS account. No protection against hostile same-user code.
- **Docker incident lab:** separated service networks and keys; agent access does
  not include backend credentials or a Docker socket. Host/Docker administrators
  remain trusted. The model container has its own writable model storage.
- **Scripted ticket pilot:** separate primary, child, operator and backend credentials,
  with specific isolation and restart checks. See [pilot security](PILOT_SECURITY.md).
- **Legacy file workspace and procurement examples:** different, weaker boundaries,
  including an unauthenticated local operator console. They do not inherit the
  current session-based console's protections.

## Outside the demonstrated guarantees

Compromised host or gateway, hostile dependency installation, arbitrary agent code,
public multi-tenant hosting, production credential lifecycle, high availability,
automatic rollback, semantic correctness and universal attack prevention are outside
the demonstrated guarantees. Native or Docker setup alone does not establish them.

See [local exposure checks](LOCAL_SECURITY_BOUNDARY.md), [limitations](LIMITATIONS.md),
[control regressions](CONTROL_TEST_MAP.md) and [dated validation](STABILIZATION_REVIEW.md).
These describe tested scope, not a completed independent penetration test.
