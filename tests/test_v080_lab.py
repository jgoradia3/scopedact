import json, threading, time, unittest, urllib.error, urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from scopedact.grants import SQLiteGrantRegistry
from scopedact.lab import build_gateway_server,build_tool_server,request_gateway,sign_headers
from scopedact.lifecycle import LifecycleOperator,LifecycleStore

class ServiceBoundaryLabTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.db=Path(self.temp.name)/"lab.db";self.key="agent-test-key";self.internal="gateway-only-key";self.client="agent:procurement"
        self.tool=build_tool_server("127.0.0.1",0,self.internal);tool_port=self.tool.server_address[1]
        self.gateway=build_gateway_server("127.0.0.1",0,database=self.db,config_path="config/lifecycle.json",tool_url=f"http://127.0.0.1:{tool_port}",internal_key=self.internal,client_keys={self.client:self.key});gateway_port=self.gateway.server_address[1]
        self.tool_url=f"http://127.0.0.1:{tool_port}";self.gateway_url=f"http://127.0.0.1:{gateway_port}"
        self.threads=[threading.Thread(target=x.serve_forever,daemon=True) for x in (self.tool,self.gateway)]
        for thread in self.threads:thread.start()
        status,result=request_gateway(self.gateway_url,"/v1/tasks",{"template":"default"},self.client,self.key);self.assertEqual(status,201);self.task=result["task_id"]
    def tearDown(self):
        for server in (self.gateway,self.tool):server.shutdown();server.server_close()
        self.temp.cleanup()
    def action(self,action="read",resource="invoice:123",request_id="req:lab-test"):
        return request_gateway(self.gateway_url,"/v1/actions",{"task_id":self.task,"request_id":request_id,"action":action,"resource":resource},self.client,self.key)
    def test_separate_agent_gateway_and_tool_execute_allowed_action(self):
        status,result=self.action();self.assertEqual(status,200);self.assertTrue(result["executed"]);self.assertEqual(result["decision"],"PERMISSION_GRANTED")
    def test_direct_tool_bypass_is_rejected(self):
        body=json.dumps({"action":"read","resource":"invoice:123"}).encode();request=urllib.request.Request(self.tool_url+"/execute",data=body,headers={"Content-Type":"application/json"},method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code,401)
    def test_ungranted_resource_never_executes(self):
        status,result=self.action(resource="invoice:999",request_id="req:wrong-resource");self.assertEqual(status,200);self.assertFalse(result["executed"]);self.assertEqual(result["decision"],"PERMISSION_NOT_GRANTED")
    def test_tampered_signed_body_is_rejected(self):
        path="/v1/actions";original=json.dumps({"task_id":self.task,"request_id":"req:original","action":"read","resource":"invoice:123"},sort_keys=True,separators=(",", ":")).encode();headers=sign_headers("POST",path,original,self.client,self.key);tampered=original.replace(b"invoice:123",b"invoice:999");request=urllib.request.Request(self.gateway_url+path,data=tampered,headers=headers,method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code,401)
    def test_api_nonce_replay_is_rejected(self):
        payload={"task_id":self.task,"request_id":"req:nonce","action":"read","resource":"invoice:123"};nonce="fixed-nonce";self.assertEqual(request_gateway(self.gateway_url,"/v1/actions",payload,self.client,self.key,nonce=nonce)[0],200);status,result=request_gateway(self.gateway_url,"/v1/actions",payload,self.client,self.key,nonce=nonce);self.assertEqual(status,401);self.assertIn("replay",result["error"])
    def test_stale_signed_request_is_rejected(self):
        status,result=request_gateway(self.gateway_url,"/v1/actions",{"task_id":self.task,"request_id":"req:stale","action":"read","resource":"invoice:123"},self.client,self.key,timestamp=str(int(time.time())-120));self.assertEqual(status,401);self.assertIn("timestamp",result["error"])
    def test_unknown_agent_client_is_rejected(self):
        status,result=request_gateway(self.gateway_url,"/v1/actions",{"task_id":self.task,"request_id":"req:impostor","action":"read","resource":"invoice:123"},"agent:impostor","wrong-key");self.assertEqual(status,401);self.assertIn("unknown",result["error"])
    def test_agent_has_no_self_approval_api(self):
        body=b'{"request_id":"req:any"}';headers=sign_headers("POST","/v1/approvals",body,self.client,self.key);request=urllib.request.Request(self.gateway_url+"/v1/approvals",data=body,headers=headers,method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code,404)
    def test_payment_waits_for_manual_approval_then_executes(self):
        request_id="req:manual-payment";status,before=self.action("approve_payment","invoice:123",request_id);self.assertEqual(before["decision"],"APPROVAL_REQUIRED");self.assertFalse(before["executed"])
        store=LifecycleStore(self.db);registry=SQLiteGrantRegistry(self.db)
        self.addCleanup(registry.close)
        try:LifecycleOperator(store,registry).approve(request_id,"human:test-reviewer")
        finally:store.close()
        status,after=self.action("approve_payment","invoice:123",request_id);self.assertEqual(after["decision"],"PERMISSION_GRANTED");self.assertTrue(after["executed"])
    def test_paused_task_blocks_external_agent(self):
        store=LifecycleStore(self.db);registry=SQLiteGrantRegistry(self.db)
        self.addCleanup(registry.close)
        try:LifecycleOperator(store,registry).pause(self.task)
        finally:store.close()
        status,result=self.action(request_id="req:paused-external");self.assertEqual(result["decision"],"TASK_NOT_ACTIVE");self.assertFalse(result["executed"])

if __name__=="__main__":unittest.main()
