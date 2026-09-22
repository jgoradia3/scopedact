from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scopedact import CallableTool, ScopedAct


class PublicSdkTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.tool = CallableTool("tool:test", {"read": self._read, "delete": self._delete})

    def _read(self, resource):
        self.calls.append(("read", resource)); return {"id": resource}

    def _delete(self, resource):
        self.calls.append(("delete", resource)); return True

    def test_exact_permission_allows_and_out_of_scope_never_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = ScopedAct(self.tool, audit_path=Path(directory) / "audit.jsonl")
            guard.issue_task(task_id="task:one", initiator="human:one", actor="agent:one", permissions=[("read", "item:1")])
            allowed = guard.invoke(task_id="task:one", actor="agent:one", action="read", resource="item:1")
            denied = guard.invoke(task_id="task:one", actor="agent:one", action="delete", resource="item:1")
        self.assertTrue(allowed.executed)
        self.assertEqual(denied.reason_code, "PERMISSION_NOT_GRANTED")
        self.assertEqual(self.calls, [("read", "item:1")])

    def test_approval_requires_same_request_to_be_resubmitted(self):
        guard = ScopedAct(self.tool, approval_required=["delete"])
        guard.issue_task(task_id="task:one", initiator="human:one", actor="agent:one", permissions=[("delete", "item:1")])
        first = guard.invoke(task_id="task:one", actor="agent:one", action="delete", resource="item:1", request_id="request:one")
        guard.approve("request:one", reviewer="human:reviewer")
        second = guard.invoke(task_id="task:one", actor="agent:one", action="delete", resource="item:1", request_id="request:one")
        self.assertEqual(first.reason_code, "APPROVAL_REQUIRED")
        self.assertTrue(second.executed)

    def test_revoked_task_cannot_execute(self):
        guard = ScopedAct(self.tool)
        guard.issue_task(task_id="task:one", initiator="human:one", actor="agent:one", permissions=[("read", "item:1")])
        guard.revoke("task:one")
        result = guard.invoke(task_id="task:one", actor="agent:one", action="read", resource="item:1")
        self.assertEqual(result.reason_code, "GRANT_REVOKED")
        self.assertFalse(result.executed)

    def test_pending_request_cannot_change_action_after_approval(self):
        guard = ScopedAct(self.tool, approval_required=["delete"])
        guard.issue_task(task_id="task:one", initiator="human:one", actor="agent:one", permissions=[("delete", "item:1"), ("read", "item:1")])
        guard.invoke(task_id="task:one", actor="agent:one", action="delete", resource="item:1", request_id="request:one")
        guard.approve("request:one", reviewer="human:reviewer")
        changed = guard.invoke(task_id="task:one", actor="agent:one", action="read", resource="item:1", request_id="request:one")
        self.assertEqual(changed.reason_code, "REQUEST_MISMATCH")
        self.assertFalse(changed.executed)
        self.assertEqual(self.calls, [])
