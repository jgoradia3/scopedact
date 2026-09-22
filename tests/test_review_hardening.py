from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from scopedact.audit import AuditLogger
from scopedact.dashboard import render_dashboard
from scopedact.evaluator import AuthorizationEvaluator
from scopedact.grants import SQLiteGrantRegistry
from scopedact.lifecycle import GrantIssuer, LifecycleGateway, LifecycleStore
from scopedact.models import ActionRequest, Permission
from scopedact.policy import ActionPolicy, PolicySet


class CountingTool:
    tool_name = 'tool:test'
    def __init__(self):
        self.calls = 0
    def execute(self, action, resource):
        self.calls += 1
        return 'done'


class ReviewHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db = Path(self.temp.name) / 'state.db'
        self.store = LifecycleStore(self.db)
        self.registry = SQLiteGrantRegistry(self.db)
        self.addCleanup(self.registry.close)
        permissions = {Permission('append', 'file:notes.md'), Permission('append', 'file:other.md')}
        self.store.add_authority('human:test', permissions)
        issuer = GrantIssuer(self.store, self.registry)
        for task in ('task:a', 'task:b'):
            issuer.issue(task_id=task, initiator='human:test', actor='agent:test', permissions=permissions)
        self.request = ActionRequest(request_id='request:one', task_id='task:a', actor='agent:test',
                                     tool='tool:test', action='append', resource='file:notes.md')
        self.tool = CountingTool()

    def tearDown(self):
        self.store.close()
        self.registry.close()
        self.temp.cleanup()

    def gateway(self, approval=True):
        policy = PolicySet({'append': ActionPolicy(True)}) if approval else PolicySet()
        return LifecycleGateway(AuthorizationEvaluator(self.registry), self.tool, self.store, AuditLogger(), policy)

    def test_every_canonical_field_is_bound_to_approval(self):
        gateway = self.gateway()
        self.assertEqual(gateway.invoke(self.request, input_value='reviewed').decision.reason_code, 'APPROVAL_REQUIRED')
        self.store.decide_approval(self.request.request_id, 'human:reviewer', True)
        mutations = {'task_id': 'task:b', 'actor': 'agent:other', 'tool': 'tool:other',
                     'action': 'delete', 'resource': 'file:other.md', 'parent_actor': 'agent:other'}
        for field, value in mutations.items():
            with self.subTest(field=field):
                result = gateway.invoke(replace(self.request, **{field: value}), input_value='reviewed')
                self.assertEqual(result.decision.reason_code, 'REQUEST_MISMATCH')
        self.assertEqual(gateway.invoke(self.request, input_value='substituted').decision.reason_code, 'REQUEST_MISMATCH')
        self.assertEqual(self.tool.calls, 0)
        self.assertTrue(gateway.invoke(self.request, input_value='reviewed').decision.allowed)
        self.assertEqual(self.tool.calls, 1)
        self.assertEqual(self.store.get_request(self.request.request_id)['task_id'], 'task:a')

    def test_pending_request_cannot_be_changed_before_approval(self):
        gateway = self.gateway()
        gateway.invoke(self.request)
        self.assertEqual(gateway.invoke(replace(self.request, task_id='task:b')).decision.reason_code, 'REQUEST_MISMATCH')
        self.assertEqual(self.store.get_request(self.request.request_id)['task_id'], 'task:a')

    def test_approval_screen_shows_escaped_exact_input(self):
        self.gateway().invoke(self.request, input_value='<script>alert(1)</script>')
        page = render_dashboard(self.store.snapshot())
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('file:notes.md', page)
        self.assertIn('Approve exact request', page)

    def test_approval_decision_is_terminal(self):
        self.gateway().invoke(self.request)
        self.store.decide_approval(self.request.request_id, 'human:reviewer', False)
        with self.assertRaises(ValueError):
            self.store.decide_approval(self.request.request_id, 'human:other', True)

    def test_concurrent_request_dispatches_once(self):
        self._concurrent_dispatch(False)

    def test_concurrent_approved_resumes_dispatch_once(self):
        self._concurrent_dispatch(True)

    def _concurrent_dispatch(self, approval):
        if approval:
            self.gateway().invoke(self.request)
            self.store.decide_approval(self.request.request_id, 'human:reviewer', True)
        entered = threading.Event()
        release = threading.Event()
        effects = []
        class SlowTool:
            tool_name = 'tool:test'
            def execute(self, action, resource):
                effects.append('effect')
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test synchronization')
                return 'done'
        def invoke():
            store = LifecycleStore(self.db)
            registry = SQLiteGrantRegistry(self.db)
            try:
                policy = PolicySet({'append': ActionPolicy(True)}) if approval else PolicySet()
                return LifecycleGateway(AuthorizationEvaluator(registry), SlowTool(), store, AuditLogger(), policy).invoke(self.request)
            finally:
                store.close()
                registry.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(invoke)
            try:
                self.assertTrue(entered.wait(5))
                second = pool.submit(invoke).result(timeout=5)
                self.assertEqual(second.decision.reason_code, 'REQUEST_IN_PROGRESS')
            finally:
                release.set()
            self.assertTrue(first.result(timeout=5).decision.allowed)
        self.assertEqual(effects, ['effect'])
        self.assertTrue(self.store.verify_event_chain()['valid'])

    def test_side_effect_then_failure_is_not_retried(self):
        def uncertain(action, resource):
            self.tool.calls += 1
            raise TimeoutError('response lost after side effect')
        self.tool.execute = uncertain
        gateway = self.gateway(False)
        with self.assertRaises(TimeoutError):
            gateway.invoke(self.request)
        self.assertEqual(gateway.invoke(self.request).decision.reason_code, 'REPLAY_DETECTED')
        self.assertEqual(self.tool.calls, 1)
        self.assertEqual(self.store.snapshot()['executions'][0]['state'], 'unknown')

    def test_claim_survives_restart_without_automatic_retry(self):
        self.assertIsNone(self.store.claim_request(self.request))
        reopened = LifecycleStore(self.db)
        try:
            self.assertEqual(reopened.claim_request(self.request), 'REQUEST_IN_PROGRESS')
        finally:
            reopened.close()

    def test_dispatch_evidence_failure_prevents_tool_call(self):
        gateway = self.gateway(False)
        with patch.object(self.store, 'event', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                gateway.invoke(self.request)
        self.assertEqual(self.tool.calls, 0)
        self.assertEqual(gateway.invoke(self.request).decision.reason_code, 'REPLAY_DETECTED')

    def test_legacy_pending_request_requires_reissue(self):
        from scopedact.models import Decision
        self.store.record_request(self.request, Decision(False, 'APPROVAL_REQUIRED', 'legacy'))
        self.store.request_approval(self.request.request_id, self.request.task_id)
        self.store.decide_approval(self.request.request_id, 'human:reviewer', True)
        self.assertEqual(self.gateway().invoke(self.request).decision.reason_code, 'REQUEST_REISSUE_REQUIRED')
        self.assertEqual(self.tool.calls, 0)

    def test_revoked_task_still_denied_after_approval(self):
        gateway = self.gateway()
        gateway.invoke(self.request)
        self.store.decide_approval(self.request.request_id, 'human:reviewer', True)
        self.registry.revoke(self.request.task_id)
        self.assertEqual(gateway.invoke(self.request).decision.reason_code, 'GRANT_REVOKED')
        self.assertEqual(self.tool.calls, 0)

    def test_resource_paths_are_distinct_from_identity_syntax(self):
        for resource in ('folder:.', 'file:subdir/notes.md'):
            self.assertEqual(replace(self.request, resource=resource).resource, resource)
        with self.assertRaises(ValueError):
            replace(self.request, actor='agent:../bad')
        with self.assertRaises(ValueError):
            replace(self.request, resource='file:bad\nname')

    def test_ancestor_revocation_blocks_descendant(self):
        from scopedact.models import TaskGrant, utc_now
        parent = self.registry.get('task:a')
        child = TaskGrant(task_id='task:child', initiator=parent.initiator, principal='agent:child',
                          permissions=parent.permissions, expires_at=parent.expires_at,
                          parent_task_id=parent.task_id)
        self.registry.register(child)
        evaluator = AuthorizationEvaluator(self.registry)
        request = replace(self.request, task_id=child.task_id, actor=child.principal)
        self.assertTrue(evaluator.evaluate(request).allowed)
        self.registry.revoke(parent.task_id)
        self.assertEqual(evaluator.evaluate(request).reason_code, 'ANCESTOR_INACTIVE')

    def test_missing_parent_fails_closed(self):
        from scopedact.models import TaskGrant, utc_now
        parent = self.registry.get('task:a')
        child = TaskGrant(task_id='task:child', initiator=parent.initiator, principal='agent:child',
                          permissions=parent.permissions, expires_at=parent.expires_at,
                          parent_task_id='task:missing')
        self.registry.register(child)
        request = replace(self.request, task_id=child.task_id, actor=child.principal)
        self.assertEqual(AuthorizationEvaluator(self.registry).evaluate(request).reason_code, 'INVALID_DELEGATION_CHAIN')

    def test_workspace_rejects_internal_symlink_and_parent_traversal(self):
        from scopedact.application import WorkspaceTool
        root = Path(self.temp.name) / 'files'
        root.mkdir()
        (root / 'note.md').write_text('sample')
        (root / 'alias.md').symlink_to(root / 'note.md')
        for resource in ('file:alias.md', 'file:sub/../note.md'):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                WorkspaceTool(root).execute('read', resource)


if __name__ == '__main__':
    unittest.main()
