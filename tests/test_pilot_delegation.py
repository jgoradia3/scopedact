"""Delegation checks through distinct authenticated HTTP clients and persistent state."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from tempfile import TemporaryDirectory
import threading
import unittest
from uuid import uuid4

from scopedact.pilot.backend import build_backend
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD, OPERATOR
from scopedact.pilot.connector import TicketRestConnector
from scopedact.pilot.delegation import render_lineage
from scopedact.pilot.evaluate_delegation import evaluate_delegation
from scopedact.pilot.gateway import build_gateway


class PilotDelegationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.backend=build_backend('127.0.0.1',0,database=self.root/'tool.db',key='t'*48)
        self.connector=TicketRestConnector(f'http://127.0.0.1:{self.backend.server_port}','t'*48,allow_local_http=True)
        self.gateway=self.make_gateway()
        for server in (self.backend,self.gateway):
            threading.Thread(target=server.serve_forever,daemon=True).start()
        self.clients()
        self.task=self.operator.post('/v1/tasks',{'resource':'ticket:T-100'})[1]['task_id']

    def make_gateway(self):
        return build_gateway('127.0.0.1',0,database=self.root/'gateway.db',agent_key='a'*48,
                             child_key='c'*48,operator_key='o'*48,connector=self.connector)

    def clients(self):
        self.base=f'http://127.0.0.1:{self.gateway.server_port}'
        self.parent=Client(self.base,AGENT,'a'*48)
        self.child=Client(self.base,CHILD,'c'*48)
        self.operator=Client(self.base,OPERATOR,'o'*48)

    def tearDown(self):
        for server in (self.gateway,self.backend):server.shutdown();server.server_close()
        self.temp.cleanup()

    def delegate(self,**changes):
        body={'parent_task_id':self.task,'permissions':[{'action':'read','resource':'ticket:T-100'}],'lifetime_seconds':300}
        return self.parent.post('/v1/delegations',{**body,**changes})

    def action(self,task,action='read',resource='ticket:T-100',client=None,**extra):
        body={'task_id':task,'request_id':'request:'+uuid4().hex,'action':action,'resource':resource,**extra}
        return (client or self.child).post('/v1/actions',body)

    def test_full_nineteen_check_delegated_workflow(self):
        result=evaluate_delegation(self.base,'a'*48,'c'*48,'o'*48)
        self.assertEqual(result['passed'],19)
        self.assertEqual(result['total'],19)

    def test_subset_and_expiry_are_preserved(self):
        status,grant=self.delegate()
        self.assertEqual(status,200)
        self.assertEqual(grant['permissions'],[{'action':'read','resource':'ticket:T-100'}])
        self.assertEqual(grant['actor'],CHILD)
        self.assertEqual(grant['parent_task_id'],self.task)
        self.assertTrue(self.action(grant['task_id'])[1]['executed'])
        self.assertNotIn('c'*48,json.dumps(grant))
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            parent=json.loads(db.execute('SELECT body FROM grants WHERE task_id=?',(self.task,)).fetchone()[0])
        self.assertLessEqual(datetime.fromisoformat(grant['expires_at']),datetime.fromisoformat(parent['expires_at']))

    def test_authority_and_resource_amplification_are_rejected(self):
        for permission in ({'action':'delete','resource':'ticket:T-100'}, {'action':'read','resource':'ticket:T-200'}):
            with self.subTest(permission=permission):
                self.assertEqual(self.delegate(permissions=[permission])[0],409)

    def test_invalid_and_expanded_lifetime_are_rejected(self):
        for lifetime in (True,0,-1,901,900):
            with self.subTest(lifetime=lifetime):self.assertEqual(self.delegate(lifetime_seconds=lifetime)[0],409)
        self.assertEqual(self.delegate(permissions=[])[0],400)

    def test_child_cannot_impersonate_parent_or_operator(self):
        self.assertEqual(self.action(self.task)[1]['decision'],'ACTOR_MISMATCH')
        forged=Client(self.base,AGENT,'c'*48)
        self.assertEqual(forged.post('/v1/actions',{})[0],401)
        for route in ('/v1/tasks','/v1/decision','/v1/review','/v1/task-control','/v1/reconcile','/v1/evidence','/v1/lineage','/v1/delegations'):
            with self.subTest(route=route):self.assertEqual(self.child.post(route,{})[0],403)

    def test_parent_cannot_use_child_grant(self):
        _,grant=self.delegate()
        self.assertEqual(self.action(grant['task_id'],client=self.parent)[1]['decision'],'ACTOR_MISMATCH')

    def test_parent_pause_resume_and_revocation_propagate(self):
        _,grant=self.delegate();child=grant['task_id']
        for operation,expected in [('pause','ANCESTOR_TASK_NOT_ACTIVE'),('resume','PERMISSION_GRANTED'),('revoke','ANCESTOR_INACTIVE')]:
            self.assertEqual(self.operator.post('/v1/task-control',{'task_id':self.task,'operation':operation})[0],200)
            self.assertEqual(self.action(child)[1]['decision'],expected)
        self.assertEqual(self.delegate()[0],409)

    def test_child_expiration_and_parent_expiration_are_enforced(self):
        _,grant=self.delegate()
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            body=json.loads(db.execute('SELECT body FROM grants WHERE task_id=?',(self.task,)).fetchone()[0])
            body['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            db.execute('UPDATE grants SET body=? WHERE task_id=?',(json.dumps(body),self.task))
        self.assertEqual(self.action(grant['task_id'])[1]['decision'],'ANCESTOR_INACTIVE')
        self.assertEqual(self.delegate()[0],409)
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            child=json.loads(db.execute('SELECT body FROM grants WHERE task_id=?',(grant['task_id'],)).fetchone()[0])
            child['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            db.execute('UPDATE grants SET body=? WHERE task_id=?',(json.dumps(child),grant['task_id']))
        self.assertEqual(self.action(grant['task_id'])[1]['decision'],'GRANT_EXPIRED')

    def test_lineage_is_authenticated_and_has_no_proposal_text(self):
        _,grant=self.delegate();child=grant['task_id']
        self.action(child)
        self.action(child,'update',input={'text':'do not export this content','expected_version':1})
        self.assertEqual(self.action(child,parent_actor='agent:forged')[0],400)
        status,report=self.operator.post('/v1/lineage',{'task_id':self.task})
        self.assertEqual(status,200)
        self.assertNotIn('do not export this content',json.dumps(report))
        for event in report['actions']:
            self.assertEqual(event['actor'],CHILD)
            self.assertEqual(event['parent_actor'],AGENT)
            self.assertEqual(event['delegation_id'],grant['delegation_id'])
            self.assertEqual([node['actor'] for node in event['authority_chain']],[AGENT,CHILD])
            self.assertEqual(event['initiator'],OPERATOR)
            self.assertEqual(event['tool'],'tool:tickets')
        rendered=render_lineage(report)
        for expected in (OPERATOR,AGENT,CHILD,'PERMISSION_GRANTED','PERMISSION_NOT_GRANTED'):
            self.assertIn(expected,rendered)
        evidence=self.operator.post('/v1/evidence',{})[1]
        self.assertTrue(evidence['integrity']['valid'])
        self.assertNotIn('do not export this content',json.dumps(evidence))

    def test_failed_issuance_event_rolls_back_child_authority(self):
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            before=db.execute('SELECT count(*) FROM grants').fetchone()[0]
            db.execute("CREATE TRIGGER fail_delegation BEFORE INSERT ON lifecycle_events WHEN NEW.event_type='authority_delegated' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        self.assertEqual(self.delegate()[0],503)
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            self.assertEqual(db.execute('SELECT count(*) FROM grants').fetchone()[0],before)
            self.assertEqual(db.execute('SELECT count(*) FROM lifecycle_tasks WHERE actor=?',(CHILD,)).fetchone()[0],0)

    def test_child_authority_and_lineage_survive_gateway_restart(self):
        _,grant=self.delegate();self.action(grant['task_id'])
        self.gateway.shutdown();self.gateway.server_close()
        self.gateway=self.make_gateway()
        threading.Thread(target=self.gateway.serve_forever,daemon=True).start();self.clients()
        self.assertTrue(self.action(grant['task_id'])[1]['executed'])
        report=self.operator.post('/v1/lineage',{'task_id':self.task})[1]
        self.assertEqual(len(report['actions']),2)

    def test_delegated_update_still_requires_exact_human_approval(self):
        _,grant=self.delegate(permissions=[{'action':'update','resource':'ticket:T-100'}])
        payload={'task_id':grant['task_id'],'request_id':'request:approved-child','action':'update',
                 'resource':'ticket:T-100','input':{'text':'approved child text','expected_version':1}}
        self.assertEqual(self.child.post('/v1/actions',payload)[1]['decision'],'APPROVAL_REQUIRED')
        review=self.operator.post('/v1/review',{'request_id':payload['request_id']})[1]
        self.assertEqual(review['request']['parent_actor'],AGENT)
        self.operator.post('/v1/decision',{'request_id':payload['request_id'],'digest':review['digest'],'approve':True})
        self.assertTrue(self.child.post('/v1/actions',payload)[1]['executed'])

    def test_approved_child_update_cannot_override_parent_intervention(self):
        for operation, reason in [('pause', 'ANCESTOR_TASK_NOT_ACTIVE'), ('revoke', 'ANCESTOR_INACTIVE')]:
            with self.subTest(operation=operation):
                self.task = self.operator.post('/v1/tasks', {'resource': 'ticket:T-100'})[1]['task_id']
                _, grant = self.delegate(permissions=[{'action': 'update', 'resource': 'ticket:T-100'}])
                before = self.backend_snapshot()
                payload = {'task_id': grant['task_id'], 'request_id': 'request:' + uuid4().hex,
                           'action': 'update', 'resource': 'ticket:T-100',
                           'input': {'text': 'must not execute', 'expected_version': before['version']}}
                self.assertEqual(self.child.post('/v1/actions', payload)[1]['decision'], 'APPROVAL_REQUIRED')
                review = self.operator.post('/v1/review', {'request_id': payload['request_id']})[1]
                self.assertEqual(self.operator.post('/v1/decision', {
                    'request_id': payload['request_id'], 'digest': review['digest'], 'approve': True})[0], 200)
                self.assertEqual(self.operator.post('/v1/task-control', {
                    'task_id': self.task, 'operation': operation})[0], 200)
                status, result = self.child.post('/v1/actions', payload)
                self.assertEqual(status, 200)
                self.assertEqual(result['decision'], reason)
                self.assertFalse(result['executed'])
                self.assertEqual(self.backend_snapshot(), before)
                from scopedact.pilot.backend import TicketStore
                self.assertFalse(TicketStore(self.root/'tool.db').receipt(payload['request_id'])['found'])

    def backend_snapshot(self):
        from scopedact.pilot.backend import TicketStore
        return TicketStore(self.root/'tool.db').read('T-100')

    def test_wrong_parent_and_second_generation_rejected(self):
        self.assertEqual(self.delegate(parent_task_id='task:missing')[0],409)
        _,grant=self.delegate()
        self.assertEqual(self.delegate(parent_task_id=grant['task_id'])[0],409)


if __name__=='__main__':unittest.main()
