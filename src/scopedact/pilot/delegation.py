"""One-parent permission narrowing and attributable records; no graph inference."""
from __future__ import annotations

from datetime import timedelta
import json
from ..evaluator import AuthorizationEvaluator
from ..grants import validate_child_grant
from ..lifecycle import run_id
from ..models import TaskGrant, Permission, Decision, utc_now
from .common import CHILD, TOOL, canonical


class PilotEvaluator(AuthorizationEvaluator):
    def __init__(self, registry, store):
        super().__init__(registry)
        self.store = store

    def evaluate(self, request):
        result = super().evaluate(request)
        if not result.allowed:
            return result
        grant = self.registry.get(request.task_id)
        while grant.parent_task_id:
            task = self.store.get_task(grant.parent_task_id)
            if task is None or task.status.value != 'active':
                return Decision(False, 'ANCESTOR_TASK_NOT_ACTIVE', 'An ancestor task is missing or not active.')
            grant = self.registry.get(grant.parent_task_id)
        return result


def issue_child(store, registry, actor, parent_task_id, permissions, lifetime_seconds):
    parent = registry.get(parent_task_id)
    task = store.get_task(parent_task_id)
    if parent is None or parent.principal != actor or parent.parent_task_id:
        raise ValueError('only the authenticated owner of a root grant may delegate')
    if task is None or task.status.value != 'active' or registry.is_revoked(parent_task_id):
        raise ValueError('parent task is not active')
    if type(lifetime_seconds) is not int or not 1 <= lifetime_seconds <= 900 or not permissions:
        raise ValueError('nonempty scope and lifetime from 1 to 900 seconds required')
    now = utc_now()
    child = TaskGrant(task_id=run_id('task-child'), initiator=parent.initiator, principal=CHILD,
                      permissions=frozenset(permissions), expires_at=now+timedelta(seconds=lifetime_seconds),
                      parent_task_id=parent.task_id, delegation_id=run_id('delegation'),
                      metadata={'authority_source':'single-parent-subset', 'tool':TOOL})
    validate_child_grant(parent, child, now)
    # Grant, task, and issuance event commit together. No orphan authority on failure.
    detail = canonical({'initiator':parent.initiator,'actor':actor,'child_actor':CHILD,
                        'parent_task_id':parent.task_id,'delegation_id':child.delegation_id,
                        'permissions':[p.to_dict() for p in sorted(child.permissions)],
                        'expires_at':child.expires_at.isoformat()})
    stamp = now.isoformat()
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        store.connection.execute('INSERT INTO grants(task_id,body,revoked) VALUES (?,?,0)',
                                 (child.task_id, canonical(child.to_dict())))
        store.connection.execute('INSERT INTO lifecycle_tasks VALUES (?,?,?,?,?,?)',
                                 (child.task_id,child.initiator,CHILD,'active',stamp,stamp))
        previous = store.connection.execute('SELECT event_hash FROM lifecycle_events ORDER BY event_id DESC LIMIT 1').fetchone()
        head = previous['event_hash'] if previous else ''
        fingerprint = store._event_hash(stamp,'authority_delegated',child.task_id,None,detail,head)
        store.connection.execute('INSERT INTO lifecycle_events(timestamp,event_type,task_id,request_id,details,previous_hash,event_hash) VALUES (?,?,?,?,?,?,?)',
                                 (stamp,'authority_delegated',child.task_id,None,detail,head,fingerprint))
    return child


def authority_chain(registry, task_id):
    nodes, seen = [], set()
    grant = registry.get(task_id)
    while grant:
        if grant.task_id in seen:
            raise ValueError('invalid lineage cycle')
        seen.add(grant.task_id)
        nodes.append({'task_id':grant.task_id, 'actor':grant.principal,
                      'initiator':grant.initiator, 'parent_task_id':grant.parent_task_id,
                      'delegation_id':grant.delegation_id,
                      'permissions':[p.to_dict() for p in sorted(grant.permissions)],
                      'expires_at':grant.expires_at.isoformat()})
        if not grant.parent_task_id:
            break
        grant = registry.get(grant.parent_task_id)
        if grant is None:
            raise ValueError('missing ancestor')
    return list(reversed(nodes))


def record_action(store, registry, request, decision, executed, outcome):
    chain = authority_chain(registry, request.task_id)
    leaf = chain[-1] if chain else {}
    store.event('attributed_action',request.task_id,request.request_id,{
        'initiator':chain[0]['initiator'] if chain else 'unknown',
        'actor':request.actor, 'grant_actor':leaf.get('actor'),
        'parent_actor':request.parent_actor, 'parent_task_id':leaf.get('parent_task_id'),
        'delegation_id':leaf.get('delegation_id'), 'tool':request.tool,
        'action':request.action,'resource':request.resource,'decision':decision,
        'executed':executed,'outcome':outcome,'authority_chain':chain})


def lineage_report(store, registry, task_id):
    root = registry.get(task_id)
    if root is None:
        raise ValueError('task not found')
    # Include requested task and all recorded descendants, with stored parent links.
    ids = {task_id}
    grants = [json.loads(row['body']) for row in store.connection.execute('SELECT body FROM grants')]
    while True:
        additions = {g['task_id'] for g in grants if g['parent_task_id'] in ids} - ids
        if not additions:
            break
        ids.update(additions)
    nodes = []
    for identifier in sorted(ids):
        node = authority_chain(registry,identifier)[-1]
        task = store.get_task(identifier)
        node['task_status'] = task.status.value if task else 'missing'
        node['grant_revoked'] = registry.is_revoked(identifier)
        nodes.append(node)
    actions = []
    for row in store.connection.execute("SELECT * FROM lifecycle_events WHERE event_type='attributed_action' ORDER BY event_id"):
        if row['task_id'] in ids:
            actions.append({'timestamp':row['timestamp'],'task_id':row['task_id'],
                            'request_id':row['request_id'],**json.loads(row['details'])})
    return {'schema_version':1, 'root_task_id':task_id,'initiator':root.initiator,
            'nodes':nodes,'actions':actions,
            'note':'Lineage comes from stored grants and authenticated role keys, not caller-supplied parent labels.'}


def render_lineage(report):
    lines = [f"Task {report['root_task_id']}",report['initiator']]
    def visit(identifier, indent):
        node = next(n for n in report['nodes'] if n['task_id']==identifier)
        scope = ', '.join(p['action']+' '+p['resource'] for p in node['permissions'])
        lines.append(indent+node['actor']+' ['+identifier+']')
        lines.append(indent+'  Authority: '+scope)
        for event in report['actions']:
            if event['task_id']==identifier:
                lines.append(indent+'  '+event['actor']+' -> '+event['tool']+': '+event['action']+' '+event['resource']+
                             ' | '+event['decision']+' | outcome='+str(event['outcome']))
        for child in report['nodes']:
            if child['parent_task_id']==identifier:
                visit(child['task_id'],indent+'  ')
    visit(report['root_task_id'],'  ')
    return '\n'.join(lines)
