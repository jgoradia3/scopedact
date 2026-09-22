import json
import sqlite3
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scopedact.aws_iam import AwsIamReadOnlyTool
from scopedact.dashboard import apply_operator_action, render_dashboard
from scopedact.lifecycle import LifecycleStore
from scopedact.lifecycle_config import LifecycleConfig
from scopedact.mvp import initialize_demo_task
from scopedact.workflow import run_agent_workflow

class V060PreviewTests(unittest.TestCase):
    def setUp(self): self.temp=TemporaryDirectory(); self.root=Path(self.temp.name); self.config=Path("config/lifecycle.json")
    def tearDown(self): self.temp.cleanup()
    def test_external_config_and_dashboard_operator_action(self):
        db=self.root/"task.db"; task=initialize_demo_task(db,self.config); apply_operator_action(db,"/api/task/pause",{"task_id":task})
        store=LifecycleStore(db)
        try:
            self.assertEqual(store.get_task(task).status.value,"paused")
            page=render_dashboard({**store.snapshot(),"integrity":store.verify_event_chain()},"token","nonce")
            self.assertIn("state-blocked",page); self.assertIn("data-action=\"resume\"",page)
        finally: store.close()
    def test_config_rejects_task_authority_expansion(self):
        body=json.loads(self.config.read_text()); body["task_permissions"].append({"action":"delete","resource":"invoice:123"})
        path=self.root/"bad.json"; path.write_text(json.dumps(body))
        with self.assertRaises(ValueError): LifecycleConfig.load(path)
    def test_hash_chain_detects_changed_event(self):
        db=self.root/"chain.db"; initialize_demo_task(db,self.config); store=LifecycleStore(db)
        try: self.assertTrue(store.verify_event_chain()["valid"])
        finally: store.close()
        connection=sqlite3.connect(db); connection.execute("UPDATE lifecycle_events SET details='{}' WHERE event_id=1"); connection.commit(); connection.close()
        store=LifecycleStore(db)
        try: self.assertFalse(store.verify_event_chain()["valid"])
        finally: store.close()
    def test_offline_multi_step_workflow(self):
        result=run_agent_workflow(self.root/"workflow.db",self.config)
        self.assertEqual(result.source,"deterministic"); self.assertEqual(len(result.steps),5); self.assertTrue(all(step[1] in {"PERMISSION_GRANTED","APPROVAL_REQUIRED"} for step in result.steps))
    @patch("scopedact.aws_iam.shutil.which",return_value="/usr/bin/aws")
    def test_aws_preflight_and_dry_run(self,_which):
        calls=[]
        def runner(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,json.dumps({"Account":"123","Arn":"arn:test","UserId":"U"}),"")
        tool=AwsIamReadOnlyTool(profile="sandbox",runner=runner)
        self.assertEqual(tool.preflight()["Account"],"123"); self.assertEqual(calls[0][1:3],["sts","get-caller-identity"])
        command=tool.command_for("get_role","iam-role:DemoRole"); self.assertIn("get-role",command); self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError): tool.command_for("delete_role","iam-role:DemoRole")

if __name__=="__main__": unittest.main()
