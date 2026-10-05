"""Discovery must neither disclose hidden names nor convert selection into authority."""
import json
import unittest
import test_agent as helpers
from test_agent import Model, reply
from scopedact.workspace.agent import run, resume
from uuid import uuid4


class DiscoveryTests(unittest.TestCase):
    setUp = helpers.AgentTests.setUp
    tearDown = helpers.AgentTests.tearDown
    # Reuse setup only; inherited runner tests remain useful but avoid rediscovery below.
    def search(self, **changes):
        body={'task_id':self.task,'request_id':'request:'+uuid4().hex,'query':'ABC',**changes}
        return body,self.agent.post('/v1/document-search',body)

    def setup_documents(self):
        for name in ['ABC.md','ABC.txt','ABC-secret.txt']:self.docs.import_text('doc:'+name,'PRIVATE '+name)
        self.task=self.operator.post('/v1/tasks',{'summary':'Read ABC','permissions':[
            {'action':'read','resource':'doc:ABC.md'},{'action':'read','resource':'doc:ABC.txt'}]})[1]['task_id']

    def test_filtering_choice_and_exact_read(self):
        self.setup_documents()
        state=run(Model([reply('find_document',query='ABC')]),self.agent,self.task,'Read ABC',self.state)
        self.assertEqual(state['status'],'needs_document_choice')
        self.assertEqual(set(state['search_result']['candidates']),{'doc:ABC.md','doc:ABC.txt'})
        self.assertNotIn('PRIVATE',json.dumps(state))
        self.assertNotIn('ABC-secret',json.dumps(state))
        body={'task_id':self.task,'request_id':state['search']['request_id'],'resource':'doc:ABC.txt'}
        self.assertEqual(self.agent.post('/v1/document-choice',body)[0],403)
        self.assertEqual(self.operator.post('/v1/document-choice',{**body,'resource':'doc:ABC-secret.txt'})[0],400)
        self.assertEqual(self.operator.post('/v1/document-choice',body)[0],200)
        self.assertEqual(self.operator.post('/v1/document-choice',body)[0],409)
        result=resume(self.agent,self.state)
        self.assertEqual(result['status'],'read_completed')
        self.assertEqual(result['read_result']['value']['resource'],'doc:ABC.txt')
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertEqual(report['counts']['completed'],1)
        self.assertEqual(report['searches'][0]['selected'],'doc:ABC.txt')

    def test_revocation_after_choice_rechecks_access(self):
        self.setup_documents()
        state=run(Model([reply('find_document',query='ABC')]),self.agent,self.task,'Read ABC',self.state)
        self.operator.post('/v1/document-choice',{'task_id':self.task,'request_id':state['search']['request_id'],'resource':'doc:ABC.md'})
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        result=resume(self.agent,self.state)
        self.assertEqual(result['status'],'document_unavailable')
        self.assertEqual(result['search_result']['candidates'],[])
        self.assertEqual(self.operator.post('/v1/map',{'task_id':self.task})[1]['counts']['completed'],0)

    def test_pause_search_and_binding(self):
        self.setup_documents();body,(status,result)=self.search()
        self.assertEqual(status,200)
        self.assertEqual(self.agent.post('/v1/document-search',{**body,'query':'different'})[0],409)
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'pause'})
        self.assertEqual(self.agent.post('/v1/document-search',body)[1]['status'],'unavailable')
        self.assertEqual(self.operator.post('/v1/document-choice',{'task_id':self.task,'request_id':body['request_id'],'resource':'doc:ABC.md'})[0],409)

    def test_one_match_no_match_and_blocked_read(self):
        self.setup_documents()
        self.assertEqual(self.search(query='ABC.md')[1][1]['selected'],'doc:ABC.md')
        self.assertEqual(self.search(query='ABC-secret')[1][1]['candidates'],[])
        status,result=self.agent.post('/v1/actions',{'task_id':self.task,'request_id':'request:'+uuid4().hex,'action':'read','resource':'doc:ABC-secret.txt'})
        self.assertFalse(result['executed'])
        self.assertEqual(self.operator.post('/v1/map',{'task_id':self.task})[1]['counts']['blocked'],1)

    def test_single_result_reads_without_choice(self):
        self.setup_documents()
        state=run(Model([reply('find_document',query='ABC.md'),{'role':'assistant','content':'Done'}]),self.agent,self.task,'Read ABC.md',self.state)
        self.assertEqual(state['status'],'model_finished')
        self.assertTrue(state['actions'][0]['executed'])

    def test_helper_search_is_visible_under_parent_task(self):
        from scopedact.pilot.client import Client
        from scopedact.pilot.common import CHILD
        self.setup_documents()
        _,grant=self.agent.post('/v1/delegations',{'parent_task_id':self.task,
            'permissions':[{'action':'read','resource':'doc:ABC.md'},{'action':'read','resource':'doc:ABC.txt'}],
            'lifetime_seconds':120})
        child=Client(self.agent.base,CHILD,'c'*48)
        body={'task_id':grant['task_id'],'request_id':'request:'+uuid4().hex,'query':'ABC'}
        self.assertEqual(child.post('/v1/document-search',body)[1]['status'],'needs_choice')
        report=self.operator.post('/v1/map',{'task_id':self.task})[1]
        self.assertEqual(report['searches'][0]['task_id'],grant['task_id'])
        self.operator.post('/v1/task-control',{'task_id':self.task,'operation':'revoke'})
        self.assertEqual(child.post('/v1/document-search',body)[1]['status'],'unavailable')
