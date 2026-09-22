from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scopedact.audit import AuditLogger
from scopedact.dashboard import render_dashboard, serve_dashboard
from scopedact.evaluator import AuthorizationEvaluator
from scopedact.grants import SQLiteGrantRegistry
from scopedact.lifecycle import (
    AuthorityError, GrantIssuer, LifecycleGateway, LifecycleOperator,
    LifecycleStore, TaskStatus,
)
from scopedact.models import ActionRequest, Permission
from scopedact.mvp import (
    initialize_demo_task, invoke_demo_request, run_lifecycle_aws_demo,
    run_lifecycle_demo,
)
import json
import subprocess
from unittest.mock import patch
from scopedact.policy import ActionPolicy, PolicySet
from scopedact.service import InvoiceService


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.database = Path(self.temp.name) / "lifecycle.db"
        self.store = LifecycleStore(self.database)
        self.registry = SQLiteGrantRegistry(self.database)
        self.addCleanup(self.registry.close)
        self.issuer = GrantIssuer(self.store, self.registry)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def issue(self, permissions=None):
        permissions = permissions or {Permission("read", "invoice:123")}
        self.store.add_authority("human:test", permissions)
        return self.issuer.issue(
            task_id="task:test", initiator="human:test", actor="agent:test",
            permissions=set(permissions), lifetime=timedelta(minutes=5),
        )

    def request(self, request_id="req:test", action="read"):
        return ActionRequest(
            request_id=request_id, task_id="task:test", actor="agent:test",
            parent_actor="human:test", tool="tool:invoice-service",
            action=action, resource="invoice:123",
        )

    def gateway(self, policy=None):
        return LifecycleGateway(
            AuthorizationEvaluator(self.registry), InvoiceService(), self.store,
            AuditLogger(), policy,
        )

    def test_issuer_rejects_authority_absent_from_initiator(self):
        self.store.add_authority("human:test", {Permission("read", "invoice:123")})
        with self.assertRaises(AuthorityError):
            self.issuer.issue(
                task_id="task:test", initiator="human:test", actor="agent:test",
                permissions={Permission("delete", "invoice:123")},
            )

    def test_issued_grant_and_task_are_recorded(self):
        self.issue()
        self.assertEqual(self.store.get_task("task:test").status, TaskStatus.ACTIVE)
        self.assertEqual(self.registry.get("task:test").initiator, "human:test")

    def test_request_state_survives_store_reopen(self):
        self.issue()
        result = self.gateway().invoke(self.request())
        self.assertTrue(result.decision.allowed)
        self.store.close()
        self.store = LifecycleStore(self.database)
        self.assertEqual(self.store.get_request("req:test")["reason_code"], "PERMISSION_GRANTED")

    def test_audit_logger_append_mode_preserves_prior_process_events(self):
        output = Path(self.temp.name) / "audit.jsonl"
        first = AuditLogger(output, truncate=False)
        values = dict(
            event_type="authorization_decision", task_id="task:test", initiator="human:test",
            actor="agent:test", parent_actor="human:test", tool="tool:test", action="read",
            resource="invoice:123", decision="allow", reason_code="PERMISSION_GRANTED",
            request_id="req:first",
        )
        first.record(**values)
        second = AuditLogger(output, truncate=False)
        second.record(**{**values, "request_id": "req:second"})
        self.assertEqual(len(output.read_text().splitlines()), 2)

    def test_replay_state_is_durable(self):
        self.issue()
        self.gateway().invoke(self.request())
        reopened = LifecycleStore(self.database)
        try:
            gateway = LifecycleGateway(
                AuthorizationEvaluator(self.registry), InvoiceService(), reopened, AuditLogger()
            )
            self.assertEqual(gateway.invoke(self.request()).decision.reason_code, "REPLAY_DETECTED")
            original = reopened.get_request("req:test")
            self.assertEqual(original["reason_code"], "PERMISSION_GRANTED")
            attempts = reopened.snapshot()["attempts"]
            self.assertEqual([item["reason_code"] for item in attempts], ["REPLAY_DETECTED", "PERMISSION_GRANTED"])
        finally:
            reopened.close()

    def test_approval_resumes_same_request_after_human_decision(self):
        self.issue({Permission("approve_payment", "invoice:123")})
        gateway = self.gateway(PolicySet({"approve_payment": ActionPolicy(True)}))
        request = self.request(action="approve_payment")
        self.assertEqual(gateway.invoke(request).decision.reason_code, "APPROVAL_REQUIRED")
        LifecycleOperator(self.store, self.registry).approve(request.request_id, "human:reviewer")
        self.assertEqual(gateway.invoke(request).decision.reason_code, "PERMISSION_GRANTED")

    def test_rejected_approval_is_terminal(self):
        self.issue({Permission("approve_payment", "invoice:123")})
        gateway = self.gateway(PolicySet({"approve_payment": ActionPolicy(True)}))
        request = self.request(action="approve_payment")
        gateway.invoke(request)
        LifecycleOperator(self.store, self.registry).reject(request.request_id, "human:reviewer")
        self.assertEqual(gateway.invoke(request).decision.reason_code, "APPROVAL_REJECTED")
        self.assertEqual(gateway.invoke(request).decision.reason_code, "REPLAY_DETECTED")

    def test_pause_resume_and_close(self):
        self.issue()
        operator = LifecycleOperator(self.store, self.registry)
        gateway = self.gateway()
        operator.pause("task:test")
        self.assertEqual(gateway.invoke(self.request("req:paused")).decision.reason_code, "TASK_NOT_ACTIVE")
        operator.resume("task:test")
        self.assertTrue(gateway.invoke(self.request("req:resumed")).decision.allowed)
        operator.close_task("task:test")
        self.assertEqual(gateway.invoke(self.request("req:closed")).decision.reason_code, "TASK_NOT_ACTIVE")

    def test_dashboard_escapes_values_and_renders_state(self):
        self.issue()
        self.gateway().invoke(self.request())
        page = render_dashboard(self.store.snapshot())
        self.assertIn("ScopedAct Operator Console", page)
        self.assertIn("task:test", page)
        self.assertNotIn("<script>", render_dashboard({
            "tasks": [], "requests": [], "attempts": [], "approvals": [],
            "events": [{"timestamp": "x", "event_type": "<script>", "task_id": "task:x", "request_id": None, "details": "{}"}],
        }))

    def test_dashboard_rejects_non_loopback_binding(self):
        with self.assertRaises(ValueError):
            serve_dashboard(self.database, host="0.0.0.0")

    def test_complete_lifecycle_demo(self):
        other_database = Path(self.temp.name) / "demo.db"
        result = run_lifecycle_demo(other_database)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.steps), 10)

    def test_hands_on_task_supports_pause_and_request(self):
        other_database = Path(self.temp.name) / "hands-on.db"
        task_id = initialize_demo_task(other_database)
        _, allowed = invoke_demo_request(
            other_database, task_id=task_id, action="read", resource="invoice:123"
        )
        self.assertTrue(allowed.decision.allowed)
        store = LifecycleStore(other_database)
        registry = SQLiteGrantRegistry(other_database)
        self.addCleanup(registry.close)
        try:
            LifecycleOperator(store, registry).pause(task_id)
        finally:
            store.close()
        _, blocked = invoke_demo_request(
            other_database, task_id=task_id, action="read", resource="invoice:123"
        )
        self.assertEqual(blocked.decision.reason_code, "TASK_NOT_ACTIVE")

    @patch("scopedact.aws_iam.shutil.which", return_value="/usr/bin/aws")
    def test_aws_connector_runs_through_lifecycle_issuance(self, _which):
        other_database = Path(self.temp.name) / "aws.db"
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(
                command, 0, json.dumps({"Role": {"RoleName": "DemoRole", "Arn": "arn:demo"}}), ""
            )
        task_id, result = run_lifecycle_aws_demo(
            "DemoRole", database=other_database, runner=runner
        )
        self.assertTrue(result.decision.allowed)
        self.assertTrue(task_id.startswith("task-aws-read:"))


if __name__ == "__main__":
    unittest.main()
