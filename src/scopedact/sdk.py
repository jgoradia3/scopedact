"""Small public SDK for placing ScopedAct in front of Python callables.

The SDK is deliberately local and dependency-free.  It gives integrators a
stable first boundary while the HTTP lab remains available for protocol tests.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .approvals import ApprovalRegistry
from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .gateway import ToolGateway
from .grants import GrantRegistry
from .models import ActionRequest, Permission, TaskGrant
from .policy import ActionPolicy, PolicySet


Handler = Callable[[str], Any]


class CallableTool:
    """Adapt a mapping of action names to Python functions into a protected tool."""

    def __init__(self, name: str, handlers: Mapping[str, Handler]) -> None:
        if not name.startswith("tool:"):
            raise ValueError("tool name must use the 'tool:' namespace")
        if not handlers:
            raise ValueError("at least one action handler is required")
        self.tool_name = name
        self._handlers = dict(handlers)

    def execute(self, action: str, resource: str) -> Any:
        try:
            handler = self._handlers[action]
        except KeyError as error:
            raise ValueError(f"unsupported action: {action}") from error
        return handler(resource)


@dataclass(frozen=True)
class ScopedActResult:
    """Integrator-facing decision and optional protected-tool result."""

    allowed: bool
    reason_code: str
    message: str
    executed: bool
    request_id: str
    value: Any = None


class ScopedAct:
    """Dependency-free local authorization boundary for one protected tool.

    This developer-preview API is suitable for local integrations and
    evaluation. It does not replace an identity provider or a remote policy
    service, and its registries are process-local.
    """

    def __init__(
        self,
        tool: CallableTool,
        *,
        approval_required: Iterable[str] = (),
        audit_path: str | Path | None = None,
    ) -> None:
        self.tool = tool
        self.grants = GrantRegistry()
        self.approvals = ApprovalRegistry()
        policy = PolicySet({name: ActionPolicy(True) for name in approval_required})
        self.gateway = ToolGateway(
            AuthorizationEvaluator(self.grants),
            tool,
            AuditLogger(audit_path),
            policy,
            self.approvals,
        )

    def issue_task(
        self,
        *,
        task_id: str,
        initiator: str,
        actor: str,
        permissions: Iterable[Permission | tuple[str, str]],
        lifetime: timedelta = timedelta(minutes=15),
    ) -> TaskGrant:
        """Issue one exact, expiring task grant.

        Production callers must derive this scope from authenticated upstream
        authority. This local API accepts already-reviewed authority explicitly.
        """
        if lifetime <= timedelta(0):
            raise ValueError("lifetime must be positive")
        normalized = frozenset(
            item if isinstance(item, Permission) else Permission(*item)
            for item in permissions
        )
        if not normalized:
            raise ValueError("at least one permission is required")
        grant = TaskGrant(
            task_id=task_id,
            initiator=initiator,
            principal=actor,
            permissions=normalized,
            expires_at=datetime.now(timezone.utc) + lifetime,
        )
        self.grants.register(grant)
        return grant

    def invoke(
        self,
        *,
        task_id: str,
        actor: str,
        action: str,
        resource: str,
        request_id: str | None = None,
        parent_actor: str | None = None,
    ) -> ScopedActResult:
        resolved_request_id = request_id or f"request:{uuid4().hex}"
        request = ActionRequest(
            request_id=resolved_request_id,
            task_id=task_id,
            actor=actor,
            parent_actor=parent_actor,
            tool=self.tool.tool_name,
            action=action,
            resource=resource,
        )
        result = self.gateway.invoke(request)
        return ScopedActResult(
            allowed=result.decision.allowed,
            reason_code=result.decision.reason_code,
            message=result.decision.message,
            executed=result.decision.allowed,
            request_id=resolved_request_id,
            value=result.value,
        )

    def approve(self, request_id: str, *, reviewer: str) -> None:
        """Record approval; the agent must resubmit the same pending request ID."""
        self.approvals.approve(request_id, reviewer)

    def reject(self, request_id: str, *, reviewer: str) -> None:
        self.approvals.reject(request_id, reviewer)

    def revoke(self, task_id: str) -> bool:
        return self.grants.revoke(task_id)
