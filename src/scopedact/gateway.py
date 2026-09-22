from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from threading import RLock

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .models import ActionRequest, Decision
from .models import ApprovalStatus
from .approvals import ApprovalRegistry
from .policy import PolicySet
from .tools import ProtectedTool


@dataclass(frozen=True)
class GatewayResult:
    decision: Decision
    value: Any = None


class ToolGateway:
    """Mandatory authorization boundary in front of the synthetic tool."""

    def __init__(
        self,
        evaluator: AuthorizationEvaluator,
        service: ProtectedTool,
        audit: AuditLogger,
        policy: PolicySet | None = None,
        approvals: ApprovalRegistry | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.service = service
        self.audit = audit
        self.policy = policy or PolicySet()
        self.approvals = approvals or ApprovalRegistry()
        self._lock = RLock()
        self._seen_requests: set[str] = set()
        self._pending_requests: dict[str, tuple[str, str, str, str, str]] = {}

    def invoke(self, request: ActionRequest) -> GatewayResult:
        # SDK state is local; serialize calls on this gateway instance.
        with self._lock:
            return self._invoke_locked(request)

    def _invoke_locked(self, request: ActionRequest) -> GatewayResult:
        fingerprint = (request.task_id, request.actor, request.tool, request.action, request.resource)
        pending = self._pending_requests.get(request.request_id)
        if pending is not None and pending != fingerprint:
            decision = Decision(False, "REQUEST_MISMATCH", "Pending request content cannot be changed.")
            self._seen_requests.add(request.request_id)
            self._pending_requests.pop(request.request_id, None)
        elif request.request_id in self._seen_requests:
            decision = Decision(False, "REPLAY_DETECTED", "Request identifier has already been used.")
        elif request.tool != self.service.tool_name:
            decision = Decision(False, "TOOL_MISMATCH", "Request names a tool other than the protected service.")
            self._seen_requests.add(request.request_id)
        else:
            decision = self.evaluator.evaluate(request)
            if decision.allowed and self.policy.requires_approval(request.action):
                approval = self.approvals.get(request.request_id)
                if approval is None or approval.status is ApprovalStatus.PENDING:
                    self.approvals.request(request.request_id)
                    self._pending_requests[request.request_id] = fingerprint
                    decision = Decision(False, "APPROVAL_REQUIRED", "A human approval is required.")
                elif approval.status is ApprovalStatus.REJECTED:
                    decision = Decision(False, "APPROVAL_REJECTED", "The human approval was rejected.")
            if decision.reason_code != "APPROVAL_REQUIRED":
                self._seen_requests.add(request.request_id)
                self._pending_requests.pop(request.request_id, None)
        grant = self.evaluator.registry.get(request.task_id)
        initiator = grant.initiator if grant else "unknown"
        value = self.service.execute(request.action, request.resource) if decision.allowed else None
        self.audit.record(
            event_type="authorization_decision",
            task_id=request.task_id,
            initiator=initiator,
            actor=request.actor,
            parent_actor=request.parent_actor,
            tool=request.tool,
            action=request.action,
            resource=request.resource,
            decision="allow" if decision.allowed else "deny",
            reason_code=decision.reason_code,
            request_id=request.request_id,
            details={"executed": decision.allowed},
        )
        return GatewayResult(decision, value)
