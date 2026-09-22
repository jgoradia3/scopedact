from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scopedact.application import (
    WorkspaceTool,
    build_application_gateway,
    build_workspace_tool_server,
    diagnose_application,
    initialize_application,
)
from scopedact.lab import request_gateway
from scopedact.lifecycle import LifecycleStore


class GitHubReadyApplicationTests(unittest.TestCase):
    def test_init_creates_editable_project_and_doctor_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = initialize_application(Path(directory) / ".scopedact")
            result = diagnose_application(project.directory)
            self.assertTrue(result["healthy"])
            self.assertTrue((project.workspace / "welcome.md").is_file())
            self.assertTrue((project.workspace / "notes.md").is_file())

    def test_workspace_tool_rejects_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"; root.mkdir()
            (root / "note.md").write_text("hello", encoding="utf-8")
            tool = WorkspaceTool(root)
            self.assertEqual(tool.execute("read", "file:note.md")["content"], "hello")
            with self.assertRaises(ValueError): tool.execute("read", "file:../outside.txt")

    def test_signed_end_to_end_workspace_policy_and_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            project = initialize_application(Path(directory) / ".scopedact")
            key = project.client_key.read_text(encoding="utf-8").strip()
            internal = "internal-test-key"
            tool = build_workspace_tool_server("127.0.0.1", 0, internal, project.workspace)
            gateway = build_application_gateway("127.0.0.1", 0, project=project, tool_url=f"http://127.0.0.1:{tool.server_port}", internal_key=internal)
            threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (tool, gateway)]
            for thread in threads: thread.start()
            base = f"http://127.0.0.1:{gateway.server_port}"
            try:
                status, created = request_gateway(base, "/v1/tasks", {"template": "default"}, project.actor, key)
                self.assertEqual(status, 201); task_id = created["task_id"]
                status, listing = request_gateway(base, "/v1/actions", {"task_id": task_id, "request_id": "request:list", "action": "list", "resource": "folder:."}, project.actor, key)
                self.assertEqual(status, 200)
                self.assertTrue(listing["executed"])
                self.assertIn("welcome.md", listing["value"]["entries"])
                status, read = request_gateway(base, "/v1/actions", {"task_id": task_id, "request_id": "request:read", "action": "read", "resource": "file:welcome.md"}, project.actor, key)
                self.assertEqual(status, 200); self.assertTrue(read["executed"])
                status, denied = request_gateway(base, "/v1/actions", {"task_id": task_id, "request_id": "request:delete", "action": "delete", "resource": "file:welcome.md"}, project.actor, key)
                self.assertEqual(denied["decision"], "PERMISSION_NOT_GRANTED")
                self.assertTrue((project.workspace / "welcome.md").exists())
                status, invalid = request_gateway(base, "/v1/actions", {"task_id": task_id, "request_id": "request:empty", "action": "append", "resource": "file:notes.md", "input": ""}, project.actor, key)
                self.assertEqual(status, 400); self.assertIn("1 to 4000", invalid["error"])
                append_payload = {"task_id": task_id, "request_id": "request:append", "action": "append", "resource": "file:notes.md", "input": "reviewed line"}
                _, pending = request_gateway(base, "/v1/actions", append_payload, project.actor, key)
                self.assertEqual(pending["decision"], "APPROVAL_REQUIRED")
                store = LifecycleStore(project.database)
                try: store.decide_approval("request:append", "human:test-reviewer", True)
                finally: store.close()
                _, other = request_gateway(base, "/v1/tasks", {"template": "default"}, project.actor, key)
                switched = dict(append_payload, task_id=other["task_id"])
                _, mismatch_task = request_gateway(base, "/v1/actions", switched, project.actor, key)
                self.assertEqual(mismatch_task["decision"], "REQUEST_MISMATCH")
                self.assertFalse(mismatch_task["executed"])
                self.assertNotIn("reviewed line", (project.workspace / "notes.md").read_text())
                _, approved = request_gateway(base, "/v1/actions", append_payload, project.actor, key)
                self.assertTrue(approved["executed"])
                self.assertIn("reviewed line", (project.workspace / "notes.md").read_text(encoding="utf-8"))
                changed = dict(append_payload); changed["input"] = "substituted line"
                status, mismatch = request_gateway(base, "/v1/actions", changed, project.actor, key)
                self.assertEqual(status, 400); self.assertIn("cannot be changed", mismatch["error"])
                direct = urllib.request.Request(f"http://127.0.0.1:{tool.server_port}/execute", data=b'{}', headers={"Content-Type":"application/json"}, method="POST")
                with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(direct)
                self.assertEqual(error.exception.code, 401)
            finally:
                gateway.shutdown(); tool.shutdown(); gateway.server_close(); tool.server_close()


if __name__ == "__main__":
    unittest.main()
