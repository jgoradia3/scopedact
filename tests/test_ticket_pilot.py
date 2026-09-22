from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
from contextlib import closing
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from scopedact.pilot.backend import build_backend, TicketStore
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, OPERATOR, canonical, digest
from scopedact.pilot.connector import TicketRestConnector, ExecutionContext, ConnectorError
from scopedact.pilot.evaluate import evaluate
from scopedact.pilot.gateway import build_gateway

AGENT_KEY, OPERATOR_KEY, TOOL_KEY = 'a'*48, 'o'*48, 't'*48


class TicketPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.backend = build_backend('127.0.0.1', 0, database=self.root/'tickets.db', key=TOOL_KEY)
        self.connector = TicketRestConnector(f'http://127.0.0.1:{self.backend.server_port}', TOOL_KEY, allow_local_http=True)
        self.gateway = self.make_gateway()
        for service in (self.backend, self.gateway):
            threading.Thread(target=service.serve_forever, daemon=True).start()
        self.clients()

    def make_gateway(self):
        return build_gateway('127.0.0.1', 0, database=self.root/'gateway.db',
                             agent_key=AGENT_KEY, operator_key=OPERATOR_KEY, connector=self.connector)

    def clients(self):
        self.base = f'http://127.0.0.1:{self.gateway.server_port}'
        self.agent = Client(self.base, AGENT, AGENT_KEY)
        self.operator = Client(self.base, OPERATOR, OPERATOR_KEY)

    def tearDown(self):
        for service in (self.gateway, self.backend):
            service.shutdown(); service.server_close()
        self.temp.cleanup()

    def task(self):
        status, body = self.operator.post('/v1/tasks', {'resource':'ticket:T-100'})
        self.assertEqual(status, 200)
        return body['task_id']

    def proposal(self, task=None):
        return {'task_id':task or self.task(), 'request_id':'request:'+uuid4().hex,
                'action':'update','resource':'ticket:T-100',
                'input':{'text':'Exact proposed note', 'expected_version':1}}

    def approve(self, proposal):
        self.assertEqual(self.agent.post('/v1/actions', proposal)[1]['decision'], 'APPROVAL_REQUIRED')
        status, review = self.operator.post('/v1/review', {'request_id':proposal['request_id']})
        self.assertEqual(status, 200)
        self.assertEqual(self.operator.post('/v1/decision', {'request_id':proposal['request_id'],
            'digest':review['digest'],'approve':True})[0], 200)

    def test_full_seventeen_check_evaluation(self):
        result = evaluate(self.base, AGENT_KEY, OPERATOR_KEY)
        self.assertEqual(result['passed'], 17)
        self.assertTrue(result['evidence']['content_redacted'])
        self.assertNotIn('Pilot review: suggested troubleshooting steps.', json.dumps(result['evidence']))

    def test_agent_cannot_access_any_operator_route(self):
        for path in ('/v1/tasks','/v1/review','/v1/decision','/v1/task-control','/v1/reconcile','/v1/evidence'):
            with self.subTest(path=path):
                self.assertEqual(self.agent.post(path,{})[0],403)
        self.assertEqual(self.operator.post('/v1/actions',{})[0],403)

    def test_unauthenticated_gateway_and_direct_tool_are_denied(self):
        for base, path in ((self.base,'/v1/tasks'), (self.connector.base,'/tickets/T-100/comments')):
            request = Request(base+path, data=b'{}', headers={'Content-Type':'application/json'},method='POST')
            with self.assertRaises(HTTPError) as error: urlopen(request)
            self.assertEqual(error.exception.code,401)
        wrong = TicketRestConnector(self.connector.base, AGENT_KEY, allow_local_http=True)
        with self.assertRaises(ConnectorError):
            wrong.execute_context('read','ticket:T-100',ExecutionContext('request:read','task:test',AGENT))

    def test_signed_nonce_replay_and_wrong_role_key(self):
        status,_=self.operator.post('/v1/evidence',{},nonce='same-nonce')
        self.assertEqual(status,200)
        self.assertEqual(self.operator.post('/v1/evidence',{},nonce='same-nonce')[0],401)
        forged=Client(self.base,OPERATOR,AGENT_KEY)
        self.assertEqual(forged.post('/v1/evidence',{})[0],401)

    def test_mutation_is_bound_to_task_resource_input_and_review_digest(self):
        proposed=self.proposal(); self.approve(proposed)
        for change in ({'task_id':self.task()}, {'resource':'ticket:T-200'},
                       {'input':{'text':'Substitution','expected_version':1}}):
            self.assertEqual(self.agent.post('/v1/actions',{**proposed,**change})[1]['decision'],'REQUEST_MISMATCH')
        self.assertTrue(self.agent.post('/v1/actions',proposed)[1]['executed'])
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['comments'], ['Exact proposed note'])

    def test_concurrent_approved_http_requests_execute_once(self):
        proposed=self.proposal();self.approve(proposed)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.agent.post('/v1/actions',proposed)[1],range(2)))
        self.assertEqual(sum(result['executed'] for result in results),1)
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['version'],2)

    def test_backend_idempotency_is_transactional_and_content_bound(self):
        context=ExecutionContext('request:direct','task:test',AGENT,{'text':'One','expected_version':1})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.connector.execute_context('update','ticket:T-100',context),range(2)))
        self.assertEqual(results[0],results[1])
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['comments'],['One'])
        with self.assertRaises(ConnectorError):
            self.connector.execute_context('update','ticket:T-200',context)

    def test_stale_ticket_version_does_not_mutate(self):
        proposed=self.proposal();self.approve(proposed)
        self.connector.execute_context('update','ticket:T-100',ExecutionContext('request:other','task:test',AGENT,{'text':'Other update','expected_version':1}))
        status,result=self.agent.post('/v1/actions',proposed)
        self.assertEqual(status,502)
        self.assertEqual(result['error'],'conflict')
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['comments'],['Other update'])

    def test_lost_response_reconciles_without_resubmission(self):
        proposed=self.proposal();self.approve(proposed)
        original=self.connector.execute_context
        def lose_response(action,resource,context):
            original(action,resource,context)
            raise ConnectorError('simulated_lost_response')
        self.connector.execute_context=lose_response
        self.assertEqual(self.agent.post('/v1/actions',proposed)[0],502)
        self.assertEqual(self.agent.post('/v1/actions',proposed)[1]['decision'],'REPLAY_DETECTED')
        status,reconciled=self.operator.post('/v1/reconcile',{'request_id':proposed['request_id']})
        self.assertEqual(status,200);self.assertTrue(reconciled['receipt']['found'])
        executions=self.operator.post('/v1/evidence',{})[1]['state']['executions']
        self.assertEqual(executions[0]['state'],'reconciled_success')
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['version'],2)

    def test_receipt_mismatch_cannot_mark_success(self):
        proposed=self.proposal();self.approve(proposed)
        self.connector.reconcile=lambda _: {'found':True,'fingerprint':'fake','result':{}}
        self.assertEqual(self.operator.post('/v1/reconcile',{'request_id':proposed['request_id']})[0],409)

    def test_approval_expires_without_execution(self):
        proposed=self.proposal();self.approve(proposed)
        with closing(sqlite3.connect(self.root/'gateway.db')) as db, db:
            db.execute('UPDATE lifecycle_approvals SET updated_at=?', ((datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat(),))
        self.assertEqual(self.agent.post('/v1/actions',proposed)[0],409)
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['version'],1)

    def test_gateway_restart_retains_replay_protection(self):
        proposed=self.proposal();self.approve(proposed)
        self.assertTrue(self.agent.post('/v1/actions',proposed)[1]['executed'])
        self.gateway.shutdown();self.gateway.server_close()
        self.gateway=self.make_gateway()
        threading.Thread(target=self.gateway.serve_forever,daemon=True).start();self.clients()
        self.assertEqual(self.agent.post('/v1/actions',proposed)[1]['decision'],'REPLAY_DETECTED')

    def test_revocation_and_pause_intervene_before_execution(self):
        proposed=self.proposal();self.approve(proposed)
        self.operator.post('/v1/task-control',{'task_id':proposed['task_id'],'operation':'pause'})
        self.assertEqual(self.agent.post('/v1/actions',proposed)[1]['decision'],'TASK_NOT_ACTIVE')
        self.operator.post('/v1/task-control',{'task_id':proposed['task_id'],'operation':'revoke'})
        fresh=self.proposal(proposed['task_id'])
        self.assertEqual(self.agent.post('/v1/actions',fresh)[1]['decision'],'TASK_NOT_ACTIVE')
        self.assertEqual(TicketStore(self.root/'tickets.db').read('T-100')['version'],1)


class ConnectorBoundaryTests(unittest.TestCase):
    def test_unapproved_origins_and_credential_urls_rejected(self):
        for url in ('http://169.254.169.254','http://example.com','https://u:p@example.com',
                    'https://example.com/path','https://example.com?redirect=x','file:///etc/passwd'):
            with self.subTest(url=url),self.assertRaises(ValueError):
                TicketRestConnector(url,TOOL_KEY,allow_local_http=True)

    def test_resource_cannot_supply_a_url_or_path(self):
        connector=TicketRestConnector('https://example.com',TOOL_KEY)
        for resource in ('http://localhost','ticket:../../admin','ticket:T-1?x=y','ticket:T-1/../T-2'):
            with self.subTest(resource=resource),self.assertRaises(ValueError):
                connector.execute_context('read',resource,ExecutionContext('request:test','task:test',AGENT))

    def test_redirect_does_not_forward_credentials(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302);self.send_header('Location','http://127.0.0.1:1/secret');self.end_headers()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Redirect)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            connector=TicketRestConnector(f'http://127.0.0.1:{server.server_port}',TOOL_KEY,allow_local_http=True)
            with self.assertRaises(ConnectorError) as error:connector.health()
            self.assertEqual(error.exception.category,'http_302')
        finally:server.shutdown();server.server_close()


if __name__ == '__main__':unittest.main()
