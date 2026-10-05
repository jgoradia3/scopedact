"""Security boundaries and end-to-end investigation against real HTTP clients."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4

from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD, OPERATOR
from scopedact.pilot.connector import ConnectorError
from scopedact.workspace.server import build_workspace
from scopedact.workspace.store import DocumentStore


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.docs=DocumentStore(self.root/'docs.db')
        for name in ['runbook','notes','other']:
            self.docs.import_text('doc:'+name,'PRIVATE ORIGINAL '+name)
        self.start()
        self.task=self.create()

    def start(self):
        self.server=build_workspace('127.0.0.1',0,database=self.root/'gateway.db',documents=self.docs,
            agent_key='a'*48,child_key='c'*48,operator_key='o'*48)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.operator=Client(self.base,OPERATOR,'o'*48);self.agent=Client(self.base,AGENT,'a'*48);self.child=Client(self.base,CHILD,'c'*48)

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.temp.cleanup()

    def create(self):
        status,result=self.operator.post('/v1/tasks',{'summary':'Investigate login','permissions':[
            {'action':'read','resource':'doc:runbook'},{'action':'update','resource':'doc:runbook'},
            {'action':'read','resource':'doc:notes'}]})
        self.assertEqual(status,200);return result['task_id']

    def payload(self,**changes):
        return {'task_id':self.task,'request_id':'request:'+uuid4().hex,'action':'read','resource':'doc:runbook',**changes}

    def proposal(self,**changes):
        return self.payload(action='update',input={'text':'PRIVATE PROPOSAL','expected_version':1},**changes)

    def approve(self,body):
        status,result=self.agent.post('/v1/actions',body)
        self.assertEqual(status,200);self.assertEqual(result['decision'],'APPROVAL_REQUIRED')
        review=self.operator.post('/v1/review',{'request_id':body['request_id']})[1]
        self.assertEqual(self.operator.post('/v1/decision',{'request_id':body['request_id'],'digest':review['digest'],'approve':True})[0],200)

    def test_http_approval_execution_map_and_redacted_export(self):
        self.assertTrue(self.agent.post('/v1/actions',self.payload())[1]['executed'])
        p=self.proposal();self.approve(p)
        self.assertTrue(self.agent.post('/v1/actions',p)[1]['executed'])
        self.assertEqual(self.docs.read('doc:runbook')['version'],2)
        status,report=self.operator.post('/v1/map',{'task_id':self.task})
        self.assertEqual(status,200);self.assertEqual(report['counts'],{'attempts':3,'completed':2,'held':1,'blocked':0,'uncertain':0})
        self.assertTrue(report['integrity']['valid'])
        self.assertTrue(any(e['type']=='execution_dispatch' for e in report['timeline']))
        for route,body in [('/v1/map',{'task_id':self.task}),('/v1/evidence',{})]:
            data=json.dumps(self.operator.post(route,body)[1])
            self.assertNotIn('PRIVATE ORIGINAL',data);self.assertNotIn('PRIVATE PROPOSAL',data)

    def test_investigation_labels_keep_progress_separate_from_access(self):
        item=self.operator.post('/v1/workspace',{})[1]['tasks'][0]
        self.assertEqual(item['progress'],'No actions recorded')
        self.assertTrue(item['created_at']);self.assertIsInstance(item['run_number'],int)
        self.assertEqual(item['status'],'active')
        child=self.agent.post('/v1/delegations',{'parent_task_id':self.task,
            'permissions':[{'action':'read','resource':'doc:notes'}],'lifetime_seconds':120})[1]['task_id']
        listing=self.operator.post('/v1/workspace',{})[1]['tasks']
        self.assertNotIn(child,[r['task_id'] for r in listing])
        p=self.proposal();self.approve(p)
        self.assertEqual(self.operator.post('/v1/workspace',{})[1]['tasks'][0]['progress'],'Approved; not yet applied')
        self.agent.post('/v1/actions',p)
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        item=self.operator.post('/v1/workspace',{})[1]['tasks'][0]
        self.assertTrue(item['revoked'])
        self.assertEqual(item['progress'],'Change applied; verify recovery')

    def test_agent_cannot_reach_operator_endpoints(self):
        for client in [self.agent,self.child]:
            for route in ['/v1/map','/v1/workspace','/v1/tasks','/v1/document-review','/v1/decision','/v1/task-control']:
                self.assertEqual(client.post(route,{})[0],403)
        self.assertEqual(Client(self.base,OPERATOR,'a'*48).post('/v1/workspace',{})[0],401)

    def test_mismatched_approval_and_modified_input_do_not_write(self):
        p=self.proposal();self.agent.post('/v1/actions',p)
        self.assertEqual(self.operator.post('/v1/decision',{'request_id':p['request_id'],'digest':'fake','approve':True})[0],409)
        self.approve(p)
        changed={**p,'input':{'text':'ATTACK','expected_version':1}}
        self.assertEqual(self.agent.post('/v1/actions',changed)[1]['decision'],'REQUEST_MISMATCH')
        self.assertEqual(self.docs.read('doc:runbook')['version'],1)

    def test_stale_document_and_receipt_reconciliation(self):
        p=self.proposal();self.approve(p)
        self.docs.update('doc:runbook','request:external',{'text':'New operator version','expected_version':1})
        self.assertEqual(self.agent.post('/v1/actions',p)[0],502)
        self.assertEqual(self.docs.read('doc:runbook')['text'],'New operator version')
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertEqual(report['counts']['uncertain'],1)
        receipt=self.operator.post('/v1/reconcile',{'request_id':p['request_id']})[1]
        self.assertFalse(receipt['receipt']['found'])

    def test_parent_revocation_after_child_approval(self):
        child=self.agent.post('/v1/delegations',{'parent_task_id':self.task,'permissions':[{'action':'update','resource':'doc:runbook'}],'lifetime_seconds':120})[1]['task_id']
        p=self.proposal(task_id=child)
        self.assertEqual(self.child.post('/v1/actions',p)[1]['decision'],'APPROVAL_REQUIRED')
        review=self.operator.post('/v1/review',{'request_id':p['request_id']})[1]
        self.operator.post('/v1/decision',{'request_id':p['request_id'],'digest':review['digest'],'approve':True})
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        result=self.child.post('/v1/actions',p)[1]
        self.assertFalse(result['executed']);self.assertEqual(result['decision'],'ANCESTOR_INACTIVE')
        self.assertEqual(self.docs.read('doc:runbook')['version'],1)
        self.assertFalse(self.docs.receipt(p['request_id'])['found'])

    def test_document_identifiers_never_resolve_paths(self):
        for resource in ['doc:../secret','doc:/etc/passwd','doc:folder/file','doc:%2e%2e%2fsecret','file:runbook']:
            self.assertEqual(self.agent.post('/v1/actions',self.payload(resource=resource))[0],400)
        result=self.agent.post('/v1/actions',self.payload(resource='doc:other'))[1]
        self.assertEqual(result['decision'],'PERMISSION_NOT_GRANTED')

    def test_map_groups_hundreds_of_attempts_without_losing_evidence(self):
        for _ in range(101): self.agent.post('/v1/actions',self.payload())
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertEqual(len(report['groups']),1);self.assertEqual(report['groups'][0]['count'],101)
        self.assertEqual(len(report['groups'][0]['events']),101)

    def test_concurrent_retries_have_one_document_effect(self):
        p=self.proposal();self.approve(p)
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda _:self.agent.post('/v1/actions',p)[1],range(3)))
        self.assertEqual(sum(r['executed'] for r in results),1)
        self.assertEqual(self.docs.read('doc:runbook')['version'],2)
        self.assertTrue(self.docs.receipt(p['request_id'])['found'])

    def test_restart_preserves_map_and_document_versions(self):
        p=self.proposal();self.approve(p);self.agent.post('/v1/actions',p)
        self.server.shutdown();self.server.server_close();self.start()
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertEqual(report['counts']['completed'],1)
        with closing(self.docs.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM document_versions WHERE resource=?',('doc:runbook',)).fetchone()[0],2)

    def test_console_serves_only_fixed_assets_and_rejects_foreign_origin(self):
        with urlopen(self.base+'/') as response:
            self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
            self.assertNotIn(b'oooooooo',response.read())
        for route in ['/../documents.db','/static/../../documents.db']:
            with self.assertRaises(HTTPError) as error: urlopen(self.base+route)
            error.exception.close();self.assertEqual(error.exception.code,404)
        for headers in [{'Host':'attacker.example'},{'Origin':'https://attacker.example'}]:
            req=Request(self.base+'/v1/workspace',data=b'{}',headers={'Content-Type':'application/json',**headers})
            with self.assertRaises(HTTPError) as error: urlopen(req)
            error.exception.close();self.assertEqual(error.exception.code,403)

    def test_task_scope_requires_existing_documents_and_bounded_lifetime(self):
        for permission in [{'action':'delete','resource':'doc:runbook'},{'action':'read','resource':'doc:missing'}]:
            self.assertEqual(self.operator.post('/v1/tasks',{'summary':'test','permissions':[permission]})[0],400)
        self.assertEqual(self.operator.post('/v1/tasks',{'summary':'test','permissions':[{'action':'read','resource':'doc:runbook'}],'lifetime_seconds':True})[0],400)

    def test_receipt_and_mutation_are_atomic_on_failure(self):
        with closing(self.docs.connect()) as db,db:
            db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON document_receipts BEGIN SELECT RAISE(ABORT,'test'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.docs.update('doc:runbook','request:atomic',{'text':'should rollback','expected_version':1})
        self.assertEqual(self.docs.read('doc:runbook')['version'],1)
        self.assertFalse(self.docs.receipt('request:atomic')['found'])


if __name__=='__main__': unittest.main()
