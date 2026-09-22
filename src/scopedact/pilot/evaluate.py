"""Trusted evaluation harness; intentionally holds BOTH roles. Not an agent."""
from __future__ import annotations
from statistics import median
from uuid import uuid4
from .common import AGENT, OPERATOR
from .client import Client


def evaluate(base, agent_key, operator_key):
    agent, operator = Client(base, AGENT, agent_key), Client(base, OPERATOR, operator_key)
    checks, latencies = [], []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)
    def call(client, path, body):
        status, result = client.post(path, body)
        if 'gateway_and_tool_ms' in result:
            latencies.append(result['gateway_and_tool_ms'])
        return status, result
    status, issued = call(operator, '/v1/tasks', {'resource': 'ticket:T-100'})
    check('operator creates assigned task', status == 200)
    task = issued['task_id']
    def proposal(action, resource='ticket:T-100', value=None):
        body = {'task_id': task, 'request_id': 'request:' + uuid4().hex, 'action': action, 'resource': resource}
        if value is not None:
            body['input'] = value
        return body
    _, read = call(agent, '/v1/actions', proposal('read'))
    check('assigned ticket read executes', read.get('executed') is True)
    _, outside = call(agent, '/v1/actions', proposal('read', 'ticket:T-200'))
    check('other ticket denied', outside.get('decision') == 'PERMISSION_NOT_GRANTED' and not outside['executed'])
    _, injected = call(agent, '/v1/actions', proposal('delete'))
    check('simulated malicious delete denied', injected.get('decision') == 'PERMISSION_NOT_GRANTED')
    update = proposal('update', value={'text': 'Pilot review: suggested troubleshooting steps.',
                                     'expected_version': read['value']['version']})
    _, pending = call(agent, '/v1/actions', update)
    check('update held for approval', pending.get('decision') == 'APPROVAL_REQUIRED' and not pending['executed'])
    status, _ = call(agent, '/v1/decision', {'request_id': update['request_id'], 'digest': 'fake', 'approve': True})
    check('agent cannot approve', status == 403)
    status, _ = call(agent, '/v1/tasks', {'resource': 'ticket:T-200'})
    check('agent cannot grant itself another ticket', status == 403)
    _, review = call(operator, '/v1/review', {'request_id': update['request_id']})
    check('operator sees exact update', review['request']['input'] == update['input'])
    status, _ = call(operator, '/v1/decision', {'request_id': update['request_id'], 'digest': 'wrong', 'approve': True})
    check('incorrect reviewed digest denied', status == 409)
    status, _ = call(operator, '/v1/decision', {'request_id': update['request_id'], 'digest': review['digest'], 'approve': True})
    check('exact request approved', status == 200)
    changed = dict(update, input={**update['input'], 'text': 'Substituted content'})
    _, mismatch = call(agent, '/v1/actions', changed)
    check('approved content substitution denied', mismatch.get('decision') == 'REQUEST_MISMATCH')
    _, updated = call(agent, '/v1/actions', update)
    check('approved update executes', updated.get('executed') is True)
    _, replay = call(agent, '/v1/actions', update)
    check('same request does not execute twice', replay.get('decision') == 'REPLAY_DETECTED' and not replay['executed'])
    _, confirmed = call(agent, '/v1/actions', proposal('read'))
    check('one intended comment persisted', confirmed['value']['version'] == read['value']['version'] + 1
          and len(confirmed['value']['comments']) == len(read['value']['comments']) + 1)
    _, receipt = call(operator, '/v1/reconcile', {'request_id': update['request_id']})
    check('independent backend receipt matches', receipt['receipt']['found'])
    call(operator, '/v1/task-control', {'task_id': task, 'operation': 'revoke'})
    _, revoked = call(agent, '/v1/actions', proposal('read'))
    check('acknowledged revoke blocks subsequent call', revoked.get('decision') == 'TASK_NOT_ACTIVE')
    _, evidence = call(operator, '/v1/evidence', {})
    check('event chain verifies', evidence['integrity']['valid'])
    return {'schema_version': 1, 'checks': checks, 'passed': len(checks), 'total': len(checks),
            'task_id': task, 'latency': {'samples': len(latencies),
            'median_gateway_and_tool_ms': median(latencies), 'max_gateway_and_tool_ms': max(latencies),
            'note': 'Includes tool I/O. Small synthetic sample; not a performance benchmark.'},
            'limitations': ['Scripted proposals, no real model.', 'Synthetic ticket backend.',
                            'Harness holds both roles; use agent-probe for container network isolation.'],
            'evidence': evidence}
