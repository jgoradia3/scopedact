import json
import subprocess
import unittest
from unittest.mock import patch

from scopedact.agents import OpenAICompatibleProposer, ScriptedProposer
from scopedact.aws_iam import AwsIamReadOnlyTool
from scopedact.integrations import run_agent_demo
from scopedact.audit import AuditLogger
from scopedact.evaluator import AuthorizationEvaluator
from scopedact.gateway import ToolGateway
from scopedact.grants import GrantRegistry
from scopedact.models import ActionRequest, Permission, TaskGrant, utc_now
from scopedact.service import InvoiceService
from datetime import timedelta


PROPOSAL = {
    "request_id": "req:test",
    "task_id": "task:test",
    "actor": "agent:test",
    "parent_actor": "human:test",
    "tool": "tool:test",
    "action": "read",
    "resource": "invoice:123",
}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.body).encode()


class V030IntegrationTests(unittest.TestCase):
    def test_scripted_proposer_uses_strict_request_schema(self):
        request = ScriptedProposer(PROPOSAL).propose("task", {})
        self.assertEqual(request.resource, "invoice:123")

    def test_scripted_proposer_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            ScriptedProposer({**PROPOSAL, "authorized": True}).propose("task", {})

    def test_live_adapter_parses_but_does_not_authorize(self):
        body = {"choices": [{"message": {"content": json.dumps(PROPOSAL)}}]}
        adapter = OpenAICompatibleProposer(model="test", api_key="not-real", opener=lambda *a, **k: FakeResponse(body))
        self.assertEqual(adapter.propose("task", {}).action, "read")

    def test_live_adapter_rejects_non_json(self):
        body = {"choices": [{"message": {"content": "not json"}}]}
        adapter = OpenAICompatibleProposer(model="test", api_key="not-real", opener=lambda *a, **k: FakeResponse(body))
        with self.assertRaises(ValueError):
            adapter.propose("task", {})

    def test_offline_agent_demo_executes_through_gateway(self):
        result, proposal = run_agent_demo()
        self.assertTrue(result.decision.allowed)
        self.assertEqual(proposal["resource"], "invoice:123")

    def test_gateway_rejects_mismatched_tool_binding(self):
        registry = GrantRegistry()
        registry.register(TaskGrant(
            "task:test", "human:test", "agent:test",
            frozenset({Permission("read", "invoice:123")}),
            utc_now() + timedelta(minutes=5),
        ))
        audit = AuditLogger()
        gateway = ToolGateway(AuthorizationEvaluator(registry), InvoiceService(), audit)
        request = ActionRequest.from_dict({**PROPOSAL, "tool": "tool:different"})
        result = gateway.invoke(request)
        self.assertFalse(result.decision.allowed)
        self.assertEqual(result.decision.reason_code, "TOOL_MISMATCH")

    @patch("scopedact.aws_iam.shutil.which", return_value="/usr/bin/aws")
    def test_aws_connector_uses_fixed_read_only_command(self, _which):
        captured = {}
        def runner(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, json.dumps({"Role": {"RoleName": "DemoRole", "Arn": "arn:demo"}}), "")
        value = AwsIamReadOnlyTool(runner=runner).execute("get_role", "iam-role:DemoRole")
        self.assertEqual(value["RoleName"], "DemoRole")
        self.assertEqual(captured["command"][:4], ["aws", "iam", "get-role", "--role-name"])

    def test_aws_connector_rejects_write_action_before_cli(self):
        with self.assertRaises(ValueError):
            AwsIamReadOnlyTool().execute("update_role", "iam-role:DemoRole")

    def test_aws_connector_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            AwsIamReadOnlyTool().execute("get_role", "iam-role:DemoRole;whoami")


if __name__ == "__main__":
    unittest.main()
