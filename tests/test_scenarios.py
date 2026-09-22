import json
import tempfile
import unittest
from pathlib import Path

from scopedact.scenarios import SCENARIOS, run_all


class ScenarioTests(unittest.TestCase):
    def test_all_predefined_scenarios_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.jsonl"
            results = run_all(output)
            self.assertTrue(all(result.passed for result in results))
            self.assertEqual(len(results), len(SCENARIOS))
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertGreaterEqual(len(records), 1)
            required = {"timestamp", "event_type", "task_id", "initiator", "actor", "parent_actor", "tool", "action", "resource", "decision", "reason_code", "request_id", "details"}
            self.assertTrue(all(set(record) == required for record in records))

    def test_prompt_injection_attempt_is_audited_as_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.jsonl"
            run_all(output)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            event = next(item for item in records if item["request_id"] == "req:injection-delete")
            self.assertEqual(event["decision"], "deny")
            self.assertEqual(event["reason_code"], "PERMISSION_NOT_GRANTED")


if __name__ == "__main__":
    unittest.main()

