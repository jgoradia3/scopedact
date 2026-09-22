# Python SDK integration

ScopedAct v0.11.0 exposes a small dependency-free API for protecting ordinary Python functions. Use the protected-workspace application first, then use this API to adapt an existing local function.

## Install

From a cloned or extracted repository:

```bash
python3 -m pip install -e .
python3 examples/quickstart.py
```

The quickstart adapts two functions into `CallableTool`, issues an exact read-only task grant, permits the read, and prevents a delete from reaching the function.

## Public API

- `CallableTool(name, handlers)` maps action names to functions accepting a resource string.
- `ScopedAct(tool, approval_required=..., audit_path=...)` creates a local boundary.
- `issue_task(...)` creates an exact, expiring task grant.
- `invoke(...)` returns `ScopedActResult`; callers should use `executed`, `reason_code`, and `value`.
- `approve(...)` or `reject(...)` records a human decision for a pending request.
- `revoke(...)` prevents subsequent task actions.

## Approval contract

For an approval-gated action, supply a stable namespaced request ID such as `request:payment-123`. The first invocation returns `APPROVAL_REQUIRED` and does not execute. After a reviewer calls `approve`, resubmit the same request ID. A rejected or unapproved request never reaches the handler.

## Trust boundary

The SDK is process-local and accepts reviewed task authority from the caller. It does not authenticate users, obtain entitlements from an identity provider, persist approvals, or isolate a compromised host process. Use it for development integration and architecture evaluation. The HTTP lab demonstrates a separate protocol boundary; neither path is currently a production deployment.
