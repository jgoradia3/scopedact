"""Real gateway tests with deterministic model doubles; not live-model evidence."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from scopedact.workspace.agent import run, resume, continue_after_denial, proposal, OllamaModel
from scopedact.workspace.server import build_workspace
from scopedact.workspace.store import DocumentStore
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, OPERATOR


def reply(name, **arguments):
    return {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': name, 'arguments': arguments}}]}


class Model:
    name = 'deterministic-test-double'
    def __init__(self, replies): self.replies = iter(replies)
    def chat(self, messages, tools): return next(self.replies)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.docs = DocumentStore(self.root/'docs.db'); self.docs.import_text('doc:runbook', 'Original')
        self.server = build_workspace('127.0.0.1', 0, database=self.root/'gateway.db', documents=self.docs,
            agent_key='a'*48, child_key='c'*48, operator_key='o'*48)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{self.server.server_port}'
        self.agent = Client(base, AGENT, 'a'*48); self.operator = Client(base, OPERATOR, 'o'*48)
        self.task = self.operator.post('/v1/tasks', {'summary': 'Improve runbook', 'permissions': [
            {'action': 'read', 'resource': 'doc:runbook'}, {'action': 'update', 'resource': 'doc:runbook'}]})[1]['task_id']
        self.state = self.root/'run.json'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.temp.cleanup()

    def test_denial_pauses_before_remaining_batch_and_resume_preserves_scope(self):
        batch=reply('read_document',resource='doc:forbidden')
        batch['tool_calls']+=reply('read_document',resource='doc:runbook')['tool_calls']
        result=run(Model([batch]),self.agent,self.task,'Investigate',self.state,pause_on_denial=True)
        self.assertEqual(result['status'],'paused_on_denial')
        self.assertEqual(len(result['actions']),1)
        self.assertEqual(result['discarded_calls'],1)
        self.assertEqual(self.operator.post('/v1/map',{'task_id':self.task})[1]['counts']['attempts'],1)
        # Restart-safe continuation: no in-memory model or queue is required.
        result=continue_after_denial(Model([reply('read_document',resource='doc:runbook'),{'role':'assistant','content':'done'}]),self.agent,self.state)
        self.assertEqual(result['status'],'model_finished')
        self.assertEqual(result['model_calls'],3)
        self.assertTrue(result['actions'][-1]['executed'])
        self.assertEqual(len(result['actions']),2)
        with self.assertRaises(ValueError):continue_after_denial(Model([]),self.agent,self.state)

    def test_revocation_between_denial_and_continue_still_blocks(self):
        run(Model([reply('read_document',resource='doc:forbidden')]),self.agent,self.task,'Investigate',self.state,pause_on_denial=True)
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        result=continue_after_denial(Model([reply('read_document',resource='doc:runbook')]),self.agent,self.state)
        self.assertEqual(result['status'],'denied')
        self.assertFalse(result['actions'][-1]['executed'])

    def start(self):
        return run(Model([reply('read_document', resource='doc:runbook'),
            reply('propose_update', resource='doc:runbook', text='Reviewed change')]),
            self.agent, self.task, 'Improve runbook', self.state)

    def approve(self, result):
        request = result['pending']['request_id']
        review = self.operator.post('/v1/review', {'request_id': request})[1]
        self.operator.post('/v1/decision', {'request_id': request, 'digest': review['digest'], 'approve': True})

    def test_approval_requires_exact_retry(self):
        state = self.start(); self.assertEqual(state['status'], 'awaiting_approval')
        self.assertEqual(self.docs.read('doc:runbook')['version'], 1)
        self.assertEqual(resume(self.agent, self.state)['status'], 'awaiting_approval')
        self.approve(state)
        result = resume(self.agent, self.state)
        self.assertEqual(result['status'], 'executed')
        self.assertEqual(result['confirmed_updates'], 1)
        self.assertEqual(self.docs.read('doc:runbook')['version'], 2)
        with self.assertRaises(ValueError): resume(self.agent, self.state)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_revocation_overrides_approval(self):
        state = self.start(); self.approve(state)
        self.operator.post('/v1/task-control', {'task_id': self.task, 'operation': 'revoke'})
        self.assertEqual(resume(self.agent, self.state)['status'], 'denied')
        self.assertEqual(self.docs.read('doc:runbook')['version'], 1)

    def test_out_of_scope_stops_model_loop(self):
        state = run(Model([reply('read_document', resource='doc:outside')]), self.agent,
                    self.task, 'Try another document', self.state)
        self.assertEqual(state['status'], 'denied')
        report = self.operator.post('/v1/map', {'task_id': self.task})[1]
        self.assertEqual(report['counts']['blocked'], 1)

    def test_model_cannot_choose_authority_or_other_tools(self):
        for tool in [reply('shell', command='id'), reply('read_document', resource='doc:runbook', task_id='other')]:
            with self.assertRaises(ValueError): proposal(self.task, tool['tool_calls'][0]['function'])

    def test_limits_and_existing_journal(self):
        state = run(Model([reply('read_document', resource='doc:runbook')]*3), self.agent,
                    self.task, 'Read', self.state, max_actions=1)
        self.assertEqual(state['status'], 'action_limit'); self.assertEqual(len(state['actions']), 1)
        with self.assertRaises(FileExistsError): self.start()

    def test_uncertain_dispatch_keeps_exact_request(self):
        class BrokenClient:
            def post(self, path, body): raise TimeoutError('unknown outcome')
        with self.assertRaises(TimeoutError):
            run(Model([reply('read_document', resource='doc:runbook')]), BrokenClient(), self.task, 'Read', self.state)
        state = json.loads(self.state.read_text()); self.assertEqual(state['status'], 'dispatching')
        self.assertTrue(state['pending']['request_id'])
        with self.assertRaises(ValueError): resume(self.agent, self.state)

    def test_local_model_transport_only(self):
        for url in ['https://example.com', 'http://localhost@evil.test', 'http://127.0.0.1/path']:
            with self.assertRaises(ValueError): OllamaModel('test', url)

    def test_boundary_recovery_does_not_override_revocation(self):
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        state=run(Model([reply('read_document',resource='doc:runbook')]),self.agent,self.task,'Read',self.state,continue_denied_reads=True)
        self.assertEqual(state['status'],'denied')
        self.assertFalse(state['actions'][0]['executed'])
        self.assertIsNotNone(state['pending'])

    def test_model_failure_is_recorded_without_dispatch(self):
        class FailedModel:
            name = 'failed-test-double'
            def chat(self, messages, tools): raise TimeoutError('model unavailable')
        with self.assertRaises(TimeoutError):
            run(FailedModel(), self.agent, self.task, 'Read', self.state)
        state = json.loads(self.state.read_text())
        self.assertEqual(state['status'], 'model_error'); self.assertIsNone(state['pending'])
        report = self.operator.post('/v1/map', {'task_id': self.task})[1]
        self.assertEqual(report['counts']['attempts'], 0)

    def test_model_claim_is_not_execution_evidence(self):
        state = run(Model([{'role': 'assistant', 'content': 'I updated the document.'}]),
                    self.agent, self.task, 'Improve runbook', self.state)
        self.assertEqual(state['status'], 'model_finished')
        self.assertEqual(state['confirmed_updates'], 0)
        self.assertEqual(state['model_answer_unverified'], 'I updated the document.')
        self.assertEqual(self.docs.read('doc:runbook')['version'], 1)

    def test_required_proposal_reminder_does_not_invent_execution(self):
        model=Model([{'role':'assistant','content':'Fixed.'},{'role':'assistant','content':'Cannot determine repair.'}])
        state=run(model,self.agent,self.task,'Investigate',self.state,require_proposal=True)
        self.assertTrue(state['proposal_reminder'])
        self.assertEqual(state['confirmed_updates'],0)
        self.assertEqual(state['model_calls'],2)
        self.assertEqual(self.docs.read('doc:runbook')['version'],1)

    def test_unoffered_tool_is_rejected_before_dispatch(self):
        with self.assertRaises(ValueError):
            run(Model([reply('find_document',query='runbook')]),self.agent,self.task,'Read',self.state,tools=[])
        self.assertEqual(json.loads(self.state.read_text())['status'],'rejected_model_tool')
        self.assertEqual(self.operator.post('/v1/map',{'task_id':self.task})[1]['counts']['attempts'],0)

    def test_update_version_comes_from_read_not_model(self):
        tool = {'name': 'propose_update', 'arguments': {'resource': 'doc:runbook', 'text': 'New'}}
        with self.assertRaises(ValueError): proposal(self.task, tool)
        body = proposal(self.task, tool, {'doc:runbook': 7})
        self.assertEqual(body['input']['expected_version'], 7)
        tool['arguments']['expected_version'] = 99
        with self.assertRaises(ValueError): proposal(self.task, tool, {'doc:runbook': 7})
