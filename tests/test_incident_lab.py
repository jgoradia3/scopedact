"""Live HTTP lab integration. Test approvals are automated, not human review."""
from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from uuid import uuid4
from scopedact.incident_lab.services import (ISSUER, CONFIG, LOGS, CHECK, SECRET, READABLE,
    PortalStore, call, token, validate_token, identity_service, portal_service, operations_service)
from scopedact.incident_lab.__main__ import OperationsAdapter
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD, OPERATOR, canonical
from scopedact.pilot.connector import ConnectorError
from scopedact.workspace.server import build_workspace

class LiveLabTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name);self.servers=[]
        self.store=PortalStore(self.root/'portal.db')
        identity=self.start(identity_service('127.0.0.1',0,'i'*48,'s'*48))
        self.portal=self.start(portal_service('127.0.0.1',0,'p'*48,'s'*48,self.store,identity,'i'*48,fault_key='f'*48))
        self.operations=self.start(operations_service('127.0.0.1',0,'b'*48,self.portal,'p'*48))
        self.adapter=OperationsAdapter(self.operations,'b'*48)
        base=self.start(build_workspace('127.0.0.1',0,database=self.root/'gateway.db',documents=self.adapter,
            agent_key='a'*48,child_key='c'*48,operator_key='o'*48))
        self.agent=Client(base,AGENT,'a'*48);self.child=Client(base,CHILD,'c'*48);self.operator=Client(base,OPERATOR,'o'*48)
        status,result=self.operator.post('/v1/tasks',{'summary':'Investigate real login failure','permissions':
            [{'action':'read','resource':r} for r in READABLE]+[{'action':'update','resource':CONFIG}]})
        self.assertEqual(status,200);self.task=result['task_id']
    def start(self,server):
        self.servers.append(server);threading.Thread(target=server.serve_forever,daemon=True).start()
        return f'http://127.0.0.1:{server.server_port}'
    def tearDown(self):
        for server in reversed(self.servers):server.shutdown();server.server_close()
        self.temp.cleanup()
    def action(self,resource=CHECK,**kw):
        return {'task_id':self.task,'request_id':'request:'+uuid4().hex,'action':'read','resource':resource,**kw}
    def check(self):
        status,result=self.agent.post('/v1/actions',self.action());self.assertEqual(status,200)
        self.assertTrue(result['executed']);return json.loads(result['value']['text'])
    def fault(self):
        return call(self.portal,'p'*48,'POST','/inject-fault',{'fault_key':'f'*48,'request_id':'request:'+uuid4().hex})
    def proposal(self):
        return self.action(CONFIG,action='update',input={'expected_version':self.store.config()['version'],'text':canonical({'expected_issuer':ISSUER})})
    def approve(self,p):
        status,result=self.agent.post('/v1/actions',p);self.assertEqual(status,200)
        self.assertEqual(result['decision'],'APPROVAL_REQUIRED')
        review=self.operator.post('/v1/review',{'request_id':p['request_id']})[1]
        self.assertEqual(self.operator.post('/v1/decision',{'request_id':p['request_id'],'digest':review['digest'],'approve':True})[0],200)
    def test_live_failure_approved_repair_and_verification(self):
        self.assertTrue(self.check()['passed']);self.fault();self.assertEqual(self.check()['reason'],'issuer_mismatch')
        p=self.proposal();self.approve(p);self.assertFalse(self.check()['passed'])
        self.assertTrue(self.agent.post('/v1/actions',p)[1]['executed']);self.assertTrue(self.check()['passed'])
        self.assertFalse(self.agent.post('/v1/actions',p)[1]['executed']);self.assertEqual(self.store.config()['version'],3)
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertTrue(report['integrity']['valid']);self.assertTrue(all(g['tool']=='tool:staging-operations' for g in report['groups']))
        self.assertNotIn('s'*48,json.dumps(report))
        self.assertTrue(report['verifications'][-1]['details']['passed'])
        self.assertEqual(report['verifications'][-1]['details']['config_version'],3)
    def test_parent_revoke_blocks_approved_repair_and_child(self):
        self.fault();p=self.proposal();self.approve(p)
        child=self.agent.post('/v1/delegations',{'parent_task_id':self.task,'permissions':[{'action':'read','resource':LOGS}],'lifetime_seconds':120})[1]['task_id']
        self.assertTrue(self.child.post('/v1/actions',self.action(LOGS,task_id=child))[1]['executed'])
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        self.assertFalse(self.agent.post('/v1/actions',p)[1]['executed'])
        self.assertEqual(self.child.post('/v1/actions',self.action(LOGS,task_id=child))[1]['decision'],'ANCESTOR_INACTIVE')
        self.assertFalse(self.store.receipt(p['request_id'])['found']);self.assertEqual(self.store.config()['version'],2)
    def test_restricted_resources_and_roles(self):
        self.assertEqual(self.agent.post('/v1/actions',self.action(SECRET))[1]['decision'],'PERMISSION_NOT_GRANTED')
        self.assertEqual(self.agent.post('/v1/tasks',{})[0],403)
        for key,resource in [('wrong'*12,CONFIG),('b'*48,SECRET)]:
            with self.assertRaises(ConnectorError):call(self.operations,key,'POST','/read',{'resource':resource})
        self.assertEqual(self.operator.post('/v1/tasks',{'summary':'invalid','permissions':[{'action':'update','resource':LOGS}]})[0],400)
    def test_receipt_after_real_http_timeout(self):
        self.fault();p=self.proposal();self.approve(p);original=self.store.change
        def delayed(*a,**kw):
            result=original(*a,**kw);time.sleep(.15);return result
        self.store.change=delayed
        self.adapter.update=lambda resource,identifier,value:call(self.operations,'b'*48,'POST','/update',{'resource':resource,'request_id':identifier,'input':value},timeout=.03)
        self.assertEqual(self.agent.post('/v1/actions',p)[0],502);self.assertEqual(self.store.config()['version'],3)
        self.assertTrue(self.operator.post('/v1/reconcile',{'request_id':p['request_id']})[1]['receipt']['found'])
        self.assertFalse(self.agent.post('/v1/actions',p)[1]['executed']);self.assertEqual(self.store.config()['version'],3)
    def test_no_validation_bypass_and_atomic_receipt(self):
        for text in [canonical({'expected_issuer':ISSUER}),'{}','{"validate_signature":false}','{"expected_issuer":"https://attacker.test"}']:
            with self.assertRaises(ValueError):self.store.change('request:invalid',{'text':text,'expected_version':1})
        with closing(self.store.connect()) as db,db:
            db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'test'); END")
        import sqlite3
        with self.assertRaises(sqlite3.Error):self.store.change('request:atomic',{'expected_version':1,'text':canonical({'expected_issuer':'https://identity.production.example.test'})})
        self.assertEqual(self.store.config()['version'],1);self.assertFalse(self.store.receipt('request:atomic')['found'])
    def test_token_validation(self):
        self.assertEqual(validate_token(token('s'*48),'s'*48,ISSUER),'accepted')
        self.assertEqual(validate_token(token('x'*48),'s'*48,ISSUER),'invalid_signature')
        self.assertEqual(validate_token(token('s'*48,now=0),'s'*48,ISSUER),'expired_token')
        self.assertEqual(validate_token(token('s'*48,audience='other'),'s'*48,ISSUER),'audience_mismatch')
        self.assertEqual(validate_token('not-a-token','s'*48,ISSUER),'invalid_token')

if __name__=='__main__':unittest.main()
