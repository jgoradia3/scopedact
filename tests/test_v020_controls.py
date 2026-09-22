import json
import tempfile
import unittest
from pathlib import Path

from scopedact.approvals import ApprovalRegistry
from scopedact.audit import AuditLogger
from scopedact.evaluator import AuthorizationEvaluator
from scopedact.gateway import ToolGateway
from scopedact.grants import GrantError, SQLiteGrantRegistry
from scopedact.models import ActionRequest, Permission
from scopedact.policy import PolicySet
from scopedact.scenarios import FIXED_NOW, grant
from scopedact.service import InvoiceService


class StructuredRequestTests(unittest.TestCase):
    def test_valid_request_is_parsed(self):
        request = ActionRequest.from_dict({
            "request_id": "req:one", "task_id": "task:one", "actor": "agent:primary",
            "tool": "tool:invoice-service", "action": "read", "resource": "invoice:123",
        })
        self.assertEqual(request.action, "read")

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValueError):
            ActionRequest.from_dict({
                "request_id": "req:one", "task_id": "task:one", "actor": "agent:primary",
                "tool": "tool:invoice-service", "action": "read", "resource": "invoice:123",
                "hidden_instruction": "delete everything",
            })

    def test_malformed_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            ActionRequest("req:one", "task:one", "agent:primary", "invoice-service", "read", "invoice:123")


class VersionTwoControlTests(unittest.TestCase):
    def setUp(self):
        self.registry = SQLiteGrantRegistry(":memory:")
        self.addCleanup(self.registry.close)
        self.registry.register(grant("task:control", "agent:primary", {
            Permission("read", "invoice:123"), Permission("delete", "invoice:123")
        }))
        self.approvals = ApprovalRegistry()
        policy_path = Path(__file__).parents[1] / "config" / "policy.json"
        self.gateway = ToolGateway(
            AuthorizationEvaluator(self.registry, clock=lambda: FIXED_NOW),
            InvoiceService(), AuditLogger(), PolicySet.from_json(policy_path), self.approvals,
        )

    def request(self, request_id="req:control", action="read"):
        return ActionRequest(request_id, "task:control", "agent:primary", "tool:invoice-service", action, "invoice:123")

    def test_request_id_replay_is_denied(self):
        request = self.request()
        self.assertTrue(self.gateway.invoke(request).decision.allowed)
        self.assertEqual(self.gateway.invoke(request).decision.reason_code, "REPLAY_DETECTED")

    def test_sensitive_action_waits_for_approval_then_executes(self):
        request = self.request("req:delete", "delete")
        first = self.gateway.invoke(request)
        self.assertEqual(first.decision.reason_code, "APPROVAL_REQUIRED")
        self.assertTrue(self.gateway.service.exists("123"))
        self.approvals.approve(request.request_id, "human:reviewer")
        second = self.gateway.invoke(request)
        self.assertTrue(second.decision.allowed)
        self.assertFalse(self.gateway.service.exists("123"))

    def test_rejected_approval_denies_action(self):
        request = self.request("req:rejected", "delete")
        self.gateway.invoke(request)
        self.approvals.reject(request.request_id, "human:reviewer")
        self.assertEqual(self.gateway.invoke(request).decision.reason_code, "APPROVAL_REJECTED")


class SQLiteRegistryTests(unittest.TestCase):
    def test_grant_and_revocation_survive_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "scopedact.db"
            first = SQLiteGrantRegistry(database)
            self.addCleanup(first.close)
            first.register(grant("task:persist", "agent:primary", {Permission("read", "invoice:123")}))
            first.revoke("task:persist")
            second = SQLiteGrantRegistry(database)
            self.addCleanup(second.close)
            self.assertEqual(second.get("task:persist").principal, "agent:primary")
            self.assertTrue(second.is_revoked("task:persist"))

    def test_duplicate_grant_is_rejected(self):
        registry = SQLiteGrantRegistry(":memory:")
        self.addCleanup(registry.close)
        item = grant("task:duplicate", "agent:primary", {Permission("read", "invoice:123")})
        registry.register(item)
        with self.assertRaises(GrantError):
            registry.register(item)


class PolicyTests(unittest.TestCase):
    def test_invalid_policy_shape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"actions": {"delete": {"approval_required": "yes"}}}))
            with self.assertRaises(ValueError):
                PolicySet.from_json(path)


if __name__ == "__main__":
    unittest.main()
