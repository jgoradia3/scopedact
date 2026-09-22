from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .gateway import ToolGateway
from .grants import GrantError, GrantRegistry, validate_child_grant
from .models import ActionRequest, Permission, TaskGrant
from .service import InvoiceService

FIXED_NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    passed: bool
    observed: str
    expected: str


@dataclass
class ScenarioContext:
    registry: GrantRegistry
    service: InvoiceService
    audit: AuditLogger
    gateway: ToolGateway


def make_context(output: str | Path | None = None) -> ScenarioContext:
    registry = GrantRegistry()
    service = InvoiceService()
    audit = AuditLogger(output)
    evaluator = AuthorizationEvaluator(registry, clock=lambda: FIXED_NOW)
    return ScenarioContext(registry, service, audit, ToolGateway(evaluator, service, audit))


def grant(
    task_id: str,
    principal: str,
    permissions: set[Permission],
    *,
    expires_delta: timedelta = timedelta(hours=1),
    parent_task_id: str | None = None,
) -> TaskGrant:
    return TaskGrant(
        task_id=task_id,
        initiator="human:jay",
        principal=principal,
        permissions=frozenset(permissions),
        expires_at=FIXED_NOW + expires_delta,
        parent_task_id=parent_task_id,
        delegation_id=f"delegation:{task_id}" if parent_task_id else None,
    )


def request(task_id: str, actor: str, action: str, resource: str, suffix: str) -> ActionRequest:
    return ActionRequest(
        request_id=f"req:{suffix}", task_id=task_id, actor=actor,
        parent_actor="agent:primary" if actor == "agent:invoice-reader" else "human:jay",
        tool="tool:invoice-service", action=action, resource=resource,
    )


def authorized_read(ctx: ScenarioContext) -> ScenarioResult:
    task = grant("task:read-123", "agent:primary", {Permission("read", "invoice:123")})
    ctx.registry.register(task)
    result = ctx.gateway.invoke(request(task.task_id, task.principal, "read", "invoice:123", "authorized"))
    return ScenarioResult("authorized_read", result.decision.allowed, result.decision.reason_code, "PERMISSION_GRANTED")


def unauthorized_delete(ctx: ScenarioContext) -> ScenarioResult:
    task = grant("task:readonly-123", "agent:primary", {Permission("read", "invoice:123")})
    ctx.registry.register(task)
    result = ctx.gateway.invoke(request(task.task_id, task.principal, "delete", "invoice:123", "delete"))
    passed = not result.decision.allowed and ctx.service.exists("123")
    return ScenarioResult("unauthorized_delete", passed, result.decision.reason_code, "PERMISSION_NOT_GRANTED")


def invalid_child_grant(ctx: ScenarioContext) -> ScenarioResult:
    parent = grant("task:parent", "agent:primary", {Permission("read", "invoice:123")})
    child = grant(
        "task:child", "agent:invoice-reader",
        {Permission("read", "invoice:123"), Permission("delete", "invoice:123")},
        parent_task_id=parent.task_id,
    )
    ctx.registry.register(parent)
    try:
        validate_child_grant(parent, child, FIXED_NOW)
    except GrantError as error:
        return ScenarioResult("invalid_child_grant", True, str(error), "child authority rejected")
    return ScenarioResult("invalid_child_grant", False, "accepted", "child authority rejected")


def prompt_injection(ctx: ScenarioContext) -> ScenarioResult:
    parent = grant("task:synthetic-parent", "agent:primary", {Permission("read", "invoice:999")})
    ctx.registry.register(parent)
    task = grant("task:read-untrusted", "agent:invoice-reader", {Permission("read", "invoice:999")}, parent_task_id="task:synthetic-parent")
    ctx.registry.register(task)
    read_result = ctx.gateway.invoke(request(task.task_id, task.principal, "read", "invoice:999", "injection-read"))
    # Scripted illustration: malicious invoice text causes the agent to propose deletion.
    delete_result = ctx.gateway.invoke(request(task.task_id, task.principal, "delete", "invoice:999", "injection-delete"))
    passed = read_result.decision.allowed and not delete_result.decision.allowed and ctx.service.exists("999")
    return ScenarioResult("prompt_injection", passed, delete_result.decision.reason_code, "PERMISSION_NOT_GRANTED")


def revoked_task(ctx: ScenarioContext) -> ScenarioResult:
    task = grant("task:revoke", "agent:primary", {Permission("read", "invoice:123")})
    ctx.registry.register(task)
    before = ctx.gateway.invoke(request(task.task_id, task.principal, "read", "invoice:123", "before-revoke"))
    ctx.registry.revoke(task.task_id)
    after = ctx.gateway.invoke(request(task.task_id, task.principal, "read", "invoice:123", "after-revoke"))
    passed = before.decision.allowed and not after.decision.allowed
    return ScenarioResult("revoked_task", passed, after.decision.reason_code, "GRANT_REVOKED")


def expired_task(ctx: ScenarioContext) -> ScenarioResult:
    task = grant("task:expired", "agent:primary", {Permission("read", "invoice:123")}, expires_delta=timedelta(seconds=-1))
    ctx.registry.register(task)
    result = ctx.gateway.invoke(request(task.task_id, task.principal, "read", "invoice:123", "expired"))
    return ScenarioResult("expired_task", not result.decision.allowed, result.decision.reason_code, "GRANT_EXPIRED")


def trace_reconstruction(ctx: ScenarioContext) -> ScenarioResult:
    parent = grant("task:trace-parent", "agent:primary", {Permission("read", "invoice:123")})
    child = grant("task:trace-child", "agent:invoice-reader", {Permission("read", "invoice:123")}, parent_task_id=parent.task_id)
    ctx.registry.register(parent)
    validate_child_grant(parent, child, FIXED_NOW)
    ctx.registry.register(child)
    result = ctx.gateway.invoke(request(child.task_id, child.principal, "read", "invoice:123", "trace"))
    event = ctx.audit.events[-1]
    complete = all([event.initiator, event.actor, event.parent_actor, event.tool, event.action, event.decision])
    return ScenarioResult("trace_reconstruction", bool(result.decision.allowed and complete), "complete" if complete else "incomplete", "complete")


def procurement_workflow(ctx: ScenarioContext) -> ScenarioResult:
    task = grant("task:reconcile-123", "agent:primary", {
        Permission("read", "invoice:123"), Permission("summarize", "invoice:123"),
        Permission("read", "purchase-order:456"), Permission("compare", "comparison:123-456"),
    })
    ctx.registry.register(task)
    steps = [
        ("read", "invoice:123", "workflow-invoice"),
        ("summarize", "invoice:123", "workflow-summary"),
        ("read", "purchase-order:456", "workflow-po"),
        ("compare", "comparison:123-456", "workflow-compare"),
    ]
    results = [ctx.gateway.invoke(request(task.task_id, task.principal, action, resource, suffix)) for action, resource, suffix in steps]
    sensitive = ctx.gateway.invoke(request(task.task_id, task.principal, "approve_payment", "invoice:123", "workflow-approve"))
    passed = all(item.decision.allowed for item in results) and not sensitive.decision.allowed
    observed = f"{len(results)} useful steps allowed; payment {sensitive.decision.reason_code.lower()}"
    return ScenarioResult("procurement_workflow", passed, observed, "useful workflow completes; payment denied")


SCENARIOS: dict[str, Callable[[ScenarioContext], ScenarioResult]] = {
    "authorized_read": authorized_read,
    "unauthorized_delete": unauthorized_delete,
    "invalid_child_grant": invalid_child_grant,
    "prompt_injection": prompt_injection,
    "revoked_task": revoked_task,
    "expired_task": expired_task,
    "trace_reconstruction": trace_reconstruction,
    "procurement_workflow": procurement_workflow,
}


def run_scenario(name: str, output: str | Path | None = None) -> ScenarioResult:
    return SCENARIOS[name](make_context(output))


def run_all(output: str | Path | None = None) -> list[ScenarioResult]:
    # One context preserves a single sequential audit trail; task IDs are unique.
    ctx = make_context(output)
    return [scenario(ctx) for scenario in SCENARIOS.values()]
