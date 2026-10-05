"""Scenario coherence and control outcomes over the real signed HTTP gateway."""
import unittest
import test_agent as helpers
from scopedact.workspace.incident import seed,start,investigate,action,call,CURRENT,REPORT,FIXTURE
from uuid import uuid4


class IncidentTests(unittest.TestCase):
    setUp=helpers.AgentTests.setUp
    tearDown=helpers.AgentTests.tearDown

    def prepare(self, select=True):
        seed(self.docs)
        task=start(self.operator)
        state={'task_id':task,'search':{'task_id':task,'request_id':'request:'+uuid4().hex,'query':'authentication-runbook'}}
        result=call(self.agent,'/v1/document-search',state['search'])
        self.assertEqual(result['status'],'needs_choice');self.assertEqual(len(result['candidates']),2)
        if select:call(self.operator,'/v1/document-choice',{'task_id':task,'request_id':state['search']['request_id'],'resource':CURRENT})
        return state

    def test_full_incident_approval_pause_and_single_mutation(self):
        state=self.prepare();result=investigate(self.agent,state)
        self.assertEqual(result['decision'],'APPROVAL_REQUIRED')
        self.assertEqual(self.docs.read(REPORT)['version'],1)
        for name in ['identity-signing-credentials-restricted.md','payments-prod-incident-771.md']:
            _,result=action(self.agent,state['task_id'],'doc:'+name)
            self.assertEqual(result['decision'],'PERMISSION_NOT_GRANTED');self.assertFalse(result['executed'])
        proposal=state['proposal'];review=call(self.operator,'/v1/review',{'request_id':proposal['request_id']})
        call(self.operator,'/v1/decision',{'request_id':proposal['request_id'],'digest':review['digest'],'approve':True})
        self.assertEqual(self.docs.read(REPORT)['version'],1)
        call(self.operator,'/v1/task-control',{'task_id':state['task_id'],'operation':'pause'})
        self.assertFalse(call(self.agent,'/v1/actions',proposal)['executed'])
        self.assertEqual(self.docs.read(REPORT)['version'],1)
        call(self.operator,'/v1/task-control',{'task_id':state['task_id'],'operation':'resume'})
        self.assertFalse(call(self.agent,'/v1/actions',proposal)['executed'])
        investigate(self.agent,state)
        proposal=state['proposal'];review=call(self.operator,'/v1/review',{'request_id':proposal['request_id']})
        self.assertEqual(self.docs.read(REPORT)['version'],1)
        call(self.operator,'/v1/decision',{'request_id':proposal['request_id'],'digest':review['digest'],'approve':True})
        self.assertTrue(call(self.agent,'/v1/actions',proposal)['executed'])
        call(self.agent,'/v1/actions',proposal)
        self.assertEqual(self.docs.read(REPORT)['version'],2)
        report=call(self.operator,'/v1/map',{'task_id':state['task_id']})
        self.assertTrue(report['integrity']['valid']);self.assertGreaterEqual(report['counts']['blocked'],3)
        self.assertIn('CHG-STG-882',self.docs.read(REPORT)['text'])

    def test_archived_runbook_refused(self):
        state=self.prepare(False)
        call(self.operator,'/v1/document-choice',{'task_id':state['task_id'],'request_id':state['search']['request_id'],
                                               'resource':'doc:authentication-runbook-gateway-2.3-archived.md'})
        with self.assertRaisesRegex(ValueError,'applicable'):investigate(self.agent,state)
        self.assertEqual(self.docs.read(REPORT)['version'],1)

    def test_modified_evidence_does_not_receive_canned_assessment(self):
        state=self.prepare()
        resource='doc:stg-auth-204-deployment.json'
        self.docs.update(resource,'request:fixture-change',{'text':'Different incident','expected_version':1})
        with self.assertRaisesRegex(ValueError,'evidence changed'):investigate(self.agent,state)
        self.assertNotIn('proposal',state)
        self.assertEqual(self.docs.read(REPORT)['version'],1)

    def test_seed_is_atomic_and_preserves_existing_documents(self):
        seed(self.docs);before=self.docs.catalog()
        with self.assertRaises(ValueError):seed(self.docs)
        self.assertEqual(self.docs.catalog(),before)
        for name,text in FIXTURE['documents'].items():
            self.assertEqual(self.docs.read('doc:'+name)['text'],text)
            self.assertLessEqual(len(text.encode()),8000)
