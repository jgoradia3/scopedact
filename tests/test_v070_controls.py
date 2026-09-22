import json
import os
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scopedact.authority_source import SignedBundleAuthoritySource, create_signed_bundle
from scopedact.connectors import ConnectorRegistry
from scopedact.dashboard import apply_operator_action, render_dashboard
from scopedact.evidence import create_anchor, verify_anchor
from scopedact.lifecycle import LifecycleStore
from scopedact.lifecycle_config import LifecycleConfig
from scopedact.mvp import initialize_demo_task

class FakeConnector:
    connector_name="fake"; tool_name="tool:fake"; supported_actions=frozenset({"read"})
    def health(self): return {"status":"healthy"}
    def execute(self,action,resource): return {"action":action,"resource":resource}

class V070ControlsTests(unittest.TestCase):
    def setUp(self): self.temp=TemporaryDirectory();self.root=Path(self.temp.name);self.config_path=Path("config/lifecycle.json");self.config=LifecycleConfig.load(self.config_path);self.secret="test-secret-with-enough-entropy"
    def tearDown(self): self.temp.cleanup()
    def bundle(self,**changes):
        data=create_signed_bundle(principal=self.config.initiator,permissions=self.config.upstream_authority,secret=self.secret,**changes);path=self.root/"authority.json";path.write_text(json.dumps(data));return path
    def test_signed_authority_bundle_creates_task(self):
        source=SignedBundleAuthoritySource(self.bundle(),self.secret);db=self.root/"task.db";task=initialize_demo_task(db,self.config_path,source)
        store=LifecycleStore(db)
        try:self.assertEqual(store.get_task(task).status.value,"active");self.assertTrue(any(e["event_type"]=="authority_verified" for e in store.snapshot()["events"]))
        finally:store.close()
    def test_tampered_and_expired_authority_bundles_are_rejected(self):
        path=self.bundle();body=json.loads(path.read_text());body["principal"]="human:attacker";path.write_text(json.dumps(body))
        with self.assertRaises(ValueError):SignedBundleAuthoritySource(path,self.secret).resolve(self.config.initiator)
        old=datetime.now(timezone.utc)-timedelta(hours=2);path=self.bundle(now=old,lifetime_minutes=30)
        with self.assertRaises(ValueError):SignedBundleAuthoritySource(path,self.secret).resolve(self.config.initiator)
    def test_anchor_detects_tail_deletion(self):
        db=self.root/"events.db";initialize_demo_task(db,self.config_path);anchor=self.root/"anchor.json";create_anchor(db,anchor,self.secret);self.assertTrue(verify_anchor(db,anchor,self.secret)["valid"])
        connection=sqlite3.connect(db);connection.execute("DELETE FROM lifecycle_events WHERE event_id=(SELECT MAX(event_id) FROM lifecycle_events)");connection.commit();connection.close()
        self.assertEqual(verify_anchor(db,anchor,self.secret)["reason"],"ANCHOR_MISMATCH")
    def test_anchor_signature_tamper_is_rejected(self):
        db=self.root/"events.db";initialize_demo_task(db,self.config_path);anchor=self.root/"anchor.json";create_anchor(db,anchor,self.secret);body=json.loads(anchor.read_text());body["events"]+=1;anchor.write_text(json.dumps(body));self.assertEqual(verify_anchor(db,anchor,self.secret)["reason"],"ANCHOR_SIGNATURE_INVALID")
    def test_connector_registry_contract(self):
        registry=ConnectorRegistry();registry.register(FakeConnector());self.assertEqual(registry.describe()[0].actions,("read",));self.assertEqual(registry.check_health("fake")["status"],"healthy")
        with self.assertRaises(ValueError):registry.register(FakeConnector())
    def test_dashboard_guided_task_creation(self):
        db=self.root/"guided.db";page=render_dashboard({"tasks":[],"attempts":[],"approvals":[],"events":[],"grants":[]},"token","nonce");self.assertIn("Review and create task",page)
        apply_operator_action(db,"/api/task/create",{"template":"default"},self.config_path);store=LifecycleStore(db)
        try:self.assertEqual(len(store.snapshot()["tasks"]),1)
        finally:store.close()

if __name__=="__main__":unittest.main()
