import unittest
from datetime import timedelta

from scopedact.grants import GrantError, validate_child_grant
from scopedact.models import Permission
from scopedact.scenarios import FIXED_NOW, grant


class DelegationTests(unittest.TestCase):
    def setUp(self):
        self.parent = grant("task:parent-test", "agent:primary", {
            Permission("read", "invoice:123"), Permission("summarize", "invoice:123")
        })

    def test_narrowed_child_is_valid(self):
        child = grant("task:child-test", "agent:invoice-reader", {Permission("read", "invoice:123")}, parent_task_id=self.parent.task_id)
        validate_child_grant(self.parent, child, FIXED_NOW)

    def test_expanded_child_is_rejected(self):
        child = grant("task:child-test", "agent:invoice-reader", {Permission("delete", "invoice:123")}, parent_task_id=self.parent.task_id)
        with self.assertRaises(GrantError):
            validate_child_grant(self.parent, child, FIXED_NOW)

    def test_later_child_expiration_is_rejected(self):
        child = grant("task:child-test", "agent:invoice-reader", {Permission("read", "invoice:123")}, expires_delta=timedelta(hours=2), parent_task_id=self.parent.task_id)
        with self.assertRaises(GrantError):
            validate_child_grant(self.parent, child, FIXED_NOW)

    def test_different_initiator_is_rejected(self):
        child = grant("task:child-test", "agent:invoice-reader", {Permission("read", "invoice:123")}, parent_task_id=self.parent.task_id)
        child.initiator = "human:other"
        with self.assertRaises(GrantError):
            validate_child_grant(self.parent, child, FIXED_NOW)


if __name__ == "__main__":
    unittest.main()

