import unittest
from datetime import timedelta

from scopedact.evaluator import AuthorizationEvaluator
from scopedact.grants import GrantRegistry
from scopedact.models import ActionRequest, Permission
from scopedact.scenarios import FIXED_NOW, grant


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.registry = GrantRegistry()
        self.evaluator = AuthorizationEvaluator(self.registry, clock=lambda: FIXED_NOW)

    def evaluate(self, task_id="task:test", actor="agent:primary", action="read", resource="invoice:123"):
        return self.evaluator.evaluate(ActionRequest("req:test", task_id, actor, "tool:invoice-service", action, resource))

    def test_exact_permission_is_allowed(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}))
        self.assertEqual(self.evaluate().reason_code, "PERMISSION_GRANTED")

    def test_unlisted_action_is_denied(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}))
        self.assertEqual(self.evaluate(action="delete").reason_code, "PERMISSION_NOT_GRANTED")

    def test_unlisted_resource_is_denied(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}))
        self.assertFalse(self.evaluate(resource="invoice:999").allowed)

    def test_actor_mismatch_is_denied(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}))
        self.assertEqual(self.evaluate(actor="agent:other").reason_code, "ACTOR_MISMATCH")

    def test_missing_grant_is_denied(self):
        self.assertEqual(self.evaluate(task_id="task:missing").reason_code, "GRANT_NOT_FOUND")

    def test_revoked_grant_is_denied(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}))
        self.registry.revoke("task:test")
        self.assertEqual(self.evaluate().reason_code, "GRANT_REVOKED")

    def test_expired_grant_is_denied(self):
        self.registry.register(grant("task:test", "agent:primary", {Permission("read", "invoice:123")}, expires_delta=timedelta(seconds=-1)))
        self.assertEqual(self.evaluate().reason_code, "GRANT_EXPIRED")


if __name__ == "__main__":
    unittest.main()

