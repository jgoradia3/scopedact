from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from .agents import ActionProposer, OpenAICompatibleProposer, ScriptedProposer
from .audit import AuditLogger
from .aws_iam import AwsIamReadOnlyTool
from .evaluator import AuthorizationEvaluator
from .gateway import GatewayResult, ToolGateway
from .grants import GrantRegistry
from .models import Permission, TaskGrant, utc_now
from .service import InvoiceService


def _grant(task_id: str, actor: str, action: str, resource: str) -> TaskGrant:
    return TaskGrant(
        task_id=task_id,
        initiator="human:operator",
        principal=actor,
        permissions=frozenset({Permission(action, resource)}),
        expires_at=utc_now() + timedelta(minutes=15),
        metadata={"demo": True},
    )


def run_agent_demo(
    *,
    live: bool = False,
    model: str = "gpt-4.1-mini",
    output: str | Path | None = None,
) -> tuple[GatewayResult, dict[str, Any]]:
    """Run one model-proposed action through the external gateway."""
    task_id, actor = "task:agent-demo", "agent:demo"
    proposal = {
        "request_id": "req:agent-demo",
        "task_id": task_id,
        "actor": actor,
        "parent_actor": "human:operator",
        "tool": "tool:invoice-service",
        "action": "read",
        "resource": "invoice:123",
    }
    proposer: ActionProposer
    if live:
        proposer = OpenAICompatibleProposer(model=model)
    else:
        proposer = ScriptedProposer(proposal)
    request = proposer.propose(
        "Read invoice 123.",
        dict(proposal),
    )
    registry = GrantRegistry()
    registry.register(_grant(task_id, actor, "read", "invoice:123"))
    audit = AuditLogger(output)
    gateway = ToolGateway(AuthorizationEvaluator(registry), InvoiceService(), audit)
    return gateway.invoke(request), request.to_dict()


def run_aws_iam_demo(
    role_name: str,
    *,
    profile: str | None = None,
    output: str | Path | None = None,
) -> GatewayResult:
    """Read one explicitly granted IAM role through ScopedAct."""
    task_id, actor = "task:aws-role-read", "agent:aws-reader"
    resource = f"iam-role:{role_name}"
    registry = GrantRegistry()
    registry.register(_grant(task_id, actor, "get_role", resource))
    audit = AuditLogger(output)
    gateway = ToolGateway(AuthorizationEvaluator(registry), AwsIamReadOnlyTool(profile=profile), audit)
    from .models import ActionRequest
    request = ActionRequest(
        request_id="req:aws-role-read",
        task_id=task_id,
        actor=actor,
        parent_actor="human:operator",
        tool="tool:aws-iam-readonly",
        action="get_role",
        resource=resource,
    )
    return gateway.invoke(request)
