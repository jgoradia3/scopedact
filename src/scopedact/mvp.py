from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .grants import SQLiteGrantRegistry
from .lifecycle import (
    AuthorityError, GrantIssuer, LifecycleGateway, LifecycleOperator,
    LifecycleStore, run_id,
)
from .models import ActionRequest, Permission
from .policy import ActionPolicy, PolicySet
from .service import InvoiceService
from .aws_iam import AwsIamReadOnlyTool
from .lifecycle_config import LifecycleConfig


@dataclass(frozen=True)
class WorkflowStep:
    label: str
    decision: str
    executed: bool
    value: object = None


@dataclass(frozen=True)
class LifecycleDemoResult:
    task_id: str
    database: str
    steps: tuple[WorkflowStep, ...]

    @property
    def passed(self) -> bool:
        expected = {
            "grant_overreach": "AUTHORITY_ISSUANCE_REJECTED",
            "read_invoice": "PERMISSION_GRANTED",
            "read_purchase_order": "PERMISSION_GRANTED",
            "compare_records": "PERMISSION_GRANTED",
            "unauthorized_delete": "PERMISSION_NOT_GRANTED",
            "payment_before_approval": "APPROVAL_REQUIRED",
            "payment_after_approval": "PERMISSION_GRANTED",
            "request_while_paused": "TASK_NOT_ACTIVE",
            "request_after_resume": "PERMISSION_GRANTED",
            "request_after_close": "TASK_NOT_ACTIVE",
        }
        return all(expected.get(step.label) == step.decision for step in self.steps)


def _request(task_id: str, action: str, resource: str, suffix: str) -> ActionRequest:
    return ActionRequest(
        request_id=run_id(f"req-{suffix}"), task_id=task_id,
        actor="agent:procurement", parent_actor="human:operator",
        tool="tool:invoice-service", action=action, resource=resource,
    )


def run_lifecycle_demo(database: str | Path, audit_output: str | Path | None = None) -> LifecycleDemoResult:
    """Run one complete local authority-lifecycle workflow."""
    database = str(database)
    store = LifecycleStore(database)
    registry = SQLiteGrantRegistry(database)
    audit = AuditLogger(audit_output, truncate=False)
    steps: list[WorkflowStep] = []
    try:
        initiator = "human:operator"
        upstream = {
            Permission("read", "invoice:123"),
            Permission("summarize", "invoice:123"),
            Permission("read", "purchase-order:456"),
            Permission("compare", "comparison:123-456"),
            Permission("approve_payment", "invoice:123"),
        }
        store.add_authority(initiator, upstream)
        issuer = GrantIssuer(store, registry)

        # Prove that the issuer cannot manufacture authority absent upstream.
        try:
            issuer.issue(
                task_id=run_id("task-overreach"), initiator=initiator,
                actor="agent:procurement", permissions={Permission("delete", "invoice:123")},
            )
        except AuthorityError as error:
            steps.append(WorkflowStep("grant_overreach", "AUTHORITY_ISSUANCE_REJECTED", False, str(error)))

        task_id = run_id("task-reconcile")
        issuer.issue(
            task_id=task_id, initiator=initiator, actor="agent:procurement",
            permissions=set(upstream),
        )
        operator = LifecycleOperator(store, registry)
        policy = PolicySet({"approve_payment": ActionPolicy(True)})
        gateway = LifecycleGateway(
            AuthorizationEvaluator(registry), InvoiceService(), store, audit, policy,
        )

        def invoke(label: str, action: str, resource: str):
            request = _request(task_id, action, resource, label)
            result = gateway.invoke(request)
            steps.append(WorkflowStep(label, result.decision.reason_code, result.decision.allowed, result.value))
            return request, result

        invoke("read_invoice", "read", "invoice:123")
        invoke("read_purchase_order", "read", "purchase-order:456")
        invoke("compare_records", "compare", "comparison:123-456")
        invoke("unauthorized_delete", "delete", "invoice:123")

        payment = _request(task_id, "approve_payment", "invoice:123", "payment")
        before = gateway.invoke(payment)
        steps.append(WorkflowStep("payment_before_approval", before.decision.reason_code, before.decision.allowed))
        operator.approve(payment.request_id, "human:reviewer")
        after = gateway.invoke(payment)
        steps.append(WorkflowStep("payment_after_approval", after.decision.reason_code, after.decision.allowed, after.value))

        operator.pause(task_id)
        invoke("request_while_paused", "read", "invoice:123")
        operator.resume(task_id)
        invoke("request_after_resume", "summarize", "invoice:123")
        operator.close_task(task_id)
        invoke("request_after_close", "read", "invoice:123")
        return LifecycleDemoResult(task_id, database, tuple(steps))
    finally:
        store.close(); registry.close()


def run_lifecycle_aws_demo(
    role_name: str,
    *,
    database: str | Path,
    profile: str | None = None,
    audit_output: str | Path | None = None,
    runner=None,
):
    """Run the read-only AWS connector through verified lifecycle issuance."""
    database = str(database)
    store = LifecycleStore(database)
    registry = SQLiteGrantRegistry(database)
    try:
        initiator, actor = "human:operator", "agent:aws-reader"
        resource = f"iam-role:{role_name}"
        permission = Permission("get_role", resource)
        store.add_authority(initiator, {permission})
        task_id = run_id("task-aws-read")
        GrantIssuer(store, registry).issue(
            task_id=task_id, initiator=initiator, actor=actor,
            permissions={permission},
        )
        options = {"profile": profile}
        if runner is not None:
            options["runner"] = runner
        tool = AwsIamReadOnlyTool(**options)
        gateway = LifecycleGateway(
            AuthorizationEvaluator(registry), tool, store, AuditLogger(audit_output, truncate=False)
        )
        request = ActionRequest(
            request_id=run_id("req-aws-read"), task_id=task_id, actor=actor,
            parent_actor=initiator, tool=tool.tool_name, action="get_role", resource=resource,
        )
        return task_id, gateway.invoke(request)
    finally:
        store.close(); registry.close()


def initialize_demo_task(database: str | Path, config_path: str | Path | None = None, authority_source=None) -> str:
    """Create one active procurement task for hands-on operator commands."""
    database = str(database)
    store = LifecycleStore(database)
    registry = SQLiteGrantRegistry(database)
    try:
        initiator = "human:operator"
        actor = "agent:procurement"
        permissions = {
            Permission("read", "invoice:123"),
            Permission("summarize", "invoice:123"),
            Permission("read", "purchase-order:456"),
            Permission("compare", "comparison:123-456"),
            Permission("approve_payment", "invoice:123"),
        }
        lifetime = timedelta(hours=1)
        if config_path is not None:
            config = LifecycleConfig.load(config_path)
            initiator, actor = config.initiator, config.actor
            upstream = config.upstream_authority
            if authority_source is not None:
                record = authority_source.resolve(initiator)
                upstream = record.permissions
                if not config.task_permissions <= upstream:
                    raise AuthorityError("configured task authority exceeds authenticated authority bundle")
                store.event("authority_verified","task:authority",None,{"principal":record.principal,"source":record.source,"key_id":record.key_id,"expires_at":record.expires_at.isoformat()})
            store.add_authority(initiator, upstream)
            permissions = set(config.task_permissions)
            lifetime = timedelta(minutes=config.grant_lifetime_minutes)
        else:
            store.add_authority(initiator, permissions)
        task_id = run_id("task-hands-on")
        GrantIssuer(store, registry).issue(
            task_id=task_id, initiator=initiator, actor=actor,
            permissions=permissions, lifetime=lifetime,
        )
        return task_id
    finally:
        store.close(); registry.close()


def invoke_demo_request(
    database: str | Path,
    *,
    task_id: str,
    action: str,
    resource: str,
    request_id: str | None = None,
    audit_output: str | Path | None = None,
):
    """Invoke the synthetic procurement tool using an existing lifecycle task."""
    database = str(database)
    store = LifecycleStore(database)
    registry = SQLiteGrantRegistry(database)
    try:
        task = store.get_task(task_id)
        if task is None:
            raise ValueError(f"unknown task: {task_id}")
        policy = PolicySet({"approve_payment": ActionPolicy(True)})
        gateway = LifecycleGateway(
            AuthorizationEvaluator(registry), InvoiceService(), store,
            AuditLogger(audit_output, truncate=False), policy,
        )
        request = ActionRequest(
            request_id=request_id or run_id("req-hands-on"), task_id=task_id,
            actor=task.actor, parent_actor=task.initiator,
            tool="tool:invoice-service", action=action, resource=resource,
        )
        return request, gateway.invoke(request)
    finally:
        store.close(); registry.close()
