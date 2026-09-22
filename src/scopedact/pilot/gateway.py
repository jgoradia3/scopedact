"""Role-authenticated pilot API; no unauthenticated operator console is started."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
import threading
from time import perf_counter

from ..audit import AuditLogger
from ..evaluator import AuthorizationEvaluator
from ..grants import SQLiteGrantRegistry
from ..lab import ApiAuthenticator
from ..lifecycle import LifecycleStore, LifecycleGateway, LifecycleOperator, GrantIssuer, run_id
from ..models import ActionRequest, Permission
from ..policy import PolicySet, ActionPolicy
from .common import AGENT, CHILD, OPERATOR, TOOL, Handler, Server, digest, canonical, ticket_id, request_id, validate_input
from .connector import ExecutionContext, ConnectorError
from .delegation import PilotEvaluator, issue_child, record_action, lineage_report


class APIError(ValueError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def fields(value, required, optional=()):
    if not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise APIError(400, 'unexpected or missing fields')


def build_gateway(host, port, *, database, agent_key, operator_key, connector, approval_ttl=300, child_key=None):
    if agent_key == operator_key or len(agent_key) < 32 or len(operator_key) < 32:
        raise ValueError('distinct strong agent and operator keys required')
    if not 1 <= approval_ttl <= 3600:
        raise ValueError('approval TTL must be 1 to 3600 seconds')
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    LifecycleStore(database).close()
    clients = {AGENT:agent_key, OPERATOR:operator_key}
    if child_key is not None:
        if len(child_key) < 32 or child_key in clients.values():
            raise ValueError('distinct strong child key required')
        clients[CHILD] = child_key
    auth = ApiAuthenticator(database, clients)
    # One service process serializes interventions with synchronous tool calls.
    # An acknowledged revoke precedes every subsequent dispatch in this process.
    execution_lock = threading.RLock()
    approval_policy = PolicySet({'update': ActionPolicy(True)})

    class GatewayHandler(Handler):
        def do_GET(self):
            if self.path == '/health':
                self.reply(200, {'status': 'healthy', 'service': 'scopedact-ticket-pilot'})
            else:
                self.reply(404, {'error': 'use authenticated POST API'})

        def do_POST(self):
            try:
                raw, body = self.body()
                actor = auth.verify('POST', self.path, raw, self.headers)
                if self.path == '/v1/actions':
                    if actor not in {AGENT, CHILD}:
                        raise APIError(403, 'agent role required')
                elif self.path == '/v1/delegations':
                    if actor != AGENT:
                        raise APIError(403, 'primary agent role required')
                elif actor != OPERATOR:
                    raise APIError(403, 'operator role required')
                with execution_lock:
                    store = LifecycleStore(database)
                    registry = SQLiteGrantRegistry(database)
                    try:
                        result = self.route(body, actor, store, registry)
                    finally:
                        store.close()
                        registry.close()
                self.reply(200, result)
            except PermissionError:
                self.reply(401, {'error': 'authentication failed'})
            except APIError as error:
                self.reply(error.status, {'error': str(error)})
            except (ValueError, TypeError, KeyError):
                self.reply(400, {'error': 'invalid request'})
            except ConnectorError as error:
                self.reply(502, {'error': error.category, 'execution': 'unknown; reconcile before retry'})
            except (OSError, sqlite3.Error):
                self.reply(503, {'error': 'service unavailable; reconcile before retry'})

        def route(self, body, actor, store, registry):
            path = self.path
            if path == '/v1/tasks':
                fields(body, {'resource'})
                ticket_id(body['resource'])
                permissions = {Permission(action, body['resource']) for action in ('read', 'update')}
                store.add_authority(OPERATOR, permissions)
                identifier = run_id('task-pilot')
                GrantIssuer(store, registry).issue(task_id=identifier, initiator=OPERATOR, actor=AGENT,
                    permissions=permissions, lifetime=timedelta(minutes=15))
                return {'task_id': identifier, 'resource': body['resource'], 'lifetime_seconds': 900}
            if path == '/v1/delegations':
                fields(body, {'parent_task_id','permissions','lifetime_seconds'})
                if CHILD not in clients:
                    raise APIError(409, 'child identity is not configured')
                values = body['permissions']
                if not isinstance(values,list) or not 1 <= len(values) <= 16:
                    raise APIError(400, 'permissions must be a bounded nonempty list')
                for permission in values:
                    if not isinstance(permission,dict):
                        raise APIError(400, 'invalid permission')
                    fields(permission, {'action','resource'})
                    ticket_id(permission['resource'])
                    if not isinstance(permission['action'],str):
                        raise APIError(400, 'invalid action')
                try:
                    child = issue_child(store,registry,actor,body['parent_task_id'],
                                        {Permission(**item) for item in values},body['lifetime_seconds'])
                except ValueError as error:
                    store.event('delegation_rejected',body['parent_task_id'],None,
                                {'actor':actor,'child_actor':CHILD,'permissions':values,
                                 'lifetime_seconds':body['lifetime_seconds'],'reason':str(error)})
                    raise APIError(409, str(error)) from None
                return {'task_id':child.task_id,'actor':child.principal,
                        'parent_task_id':child.parent_task_id,'delegation_id':child.delegation_id,
                        'permissions':[p.to_dict() for p in sorted(child.permissions)],
                        'expires_at':child.expires_at.isoformat()}
            if path == '/v1/lineage':
                fields(body, {'task_id'})
                return lineage_report(store,registry,body['task_id'])
            if path == '/v1/actions':
                fields(body, {'task_id', 'request_id', 'action', 'resource'}, {'input'})
                ticket_id(body['resource'])
                request_id(body['request_id'])
                value = body.get('input')
                if body['action'] == 'update':
                    validate_input(value)
                elif value is not None:
                    raise APIError(400, 'only update accepts input')
                grant = registry.get(body['task_id'])
                parent = registry.get(grant.parent_task_id) if grant and grant.parent_task_id else None
                parent_actor = parent.principal if parent else grant.initiator if grant else None
                request = ActionRequest(task_id=body['task_id'], request_id=body['request_id'],
                    actor=actor, parent_actor=parent_actor, tool=TOOL,
                    action=body['action'], resource=body['resource'])
                approval = store.connection.execute(
                    'SELECT * FROM lifecycle_approvals WHERE request_id=?', (request.request_id,)).fetchone()
                if approval and approval['status'] == 'approved':
                    age = datetime.now(timezone.utc) - datetime.fromisoformat(approval['updated_at'])
                    if age.total_seconds() >= approval_ttl:
                        raise APIError(409, 'approval expired; create a new proposal for review')
                context = ExecutionContext(request.request_id, request.task_id, actor, value)
                gateway = LifecycleGateway(PilotEvaluator(registry,store), connector.bind(context), store,
                    AuditLogger(database.with_suffix('.jsonl'), truncate=False), approval_policy)
                start = perf_counter()
                try:
                    result = gateway.invoke(request, input_value=value)
                except ConnectorError as error:
                    record_action(store,registry,request,'CONNECTOR_FAILURE',None,'unknown')
                    store.event('connector_failure', request.task_id, request.request_id,
                                {'category': error.category, 'outcome': 'unknown'})
                    raise
                record_action(store,registry,request,result.decision.reason_code,result.decision.allowed,
                              'succeeded' if result.decision.allowed else 'not_dispatched')
                elapsed = (perf_counter() - start) * 1000
                return {'request_id': request.request_id, 'decision': result.decision.reason_code,
                        'executed': result.decision.allowed, 'value': result.value,
                        'gateway_and_tool_ms': round(elapsed, 3)}
            if path in {'/v1/review', '/v1/decision', '/v1/reconcile'}:
                fields(body, {'request_id'} if path != '/v1/decision' else {'request_id', 'digest', 'approve'})
                request_id(body['request_id'])
                claim = store.connection.execute('SELECT * FROM execution_claims WHERE request_id=?',
                                                (body['request_id'],)).fetchone()
                if claim is None:
                    raise APIError(404, 'request not found')
                proposed = json.loads(claim['canonical'])
                if path == '/v1/review':
                    return {'request': proposed, 'digest': digest(proposed), 'execution_state': claim['state'],
                            'approval': str(store.approval_status(body['request_id']).value)
                            if store.approval_status(body['request_id']) else None,
                            'approval_ttl_seconds': approval_ttl}
                if path == '/v1/decision':
                    if type(body['approve']) is not bool or body['digest'] != digest(proposed):
                        raise APIError(409, 'reviewed request digest mismatch')
                    if claim['state'] != 'pending':
                        raise APIError(409, 'request is not awaiting approval')
                    task = store.get_task(proposed['task_id'])
                    if task is None or task.status.value != 'active':
                        raise APIError(409, 'task is not active')
                    store.decide_approval(body['request_id'], actor, body['approve'])
                    return {'request_id': body['request_id'], 'approved': body['approve']}
                if proposed['action'] != 'update':
                    raise APIError(409, 'read operations have no mutation receipt')
                context = ExecutionContext(proposed['request_id'], proposed['task_id'], proposed['actor'], proposed['input'])
                receipt = connector.reconcile(context)
                if receipt.get('found'):
                    expected = digest({'resource': proposed['resource'], 'input': proposed['input']})
                    if receipt.get('fingerprint') != expected:
                        raise APIError(409, 'receipt does not match canonical operation')
                    if claim['state'] in {'unknown', 'evaluating'}:
                        store.finish_claim(body['request_id'], 'reconciled_success')
                store.event('reconciliation', proposed['task_id'], body['request_id'],
                            {'receipt_found': bool(receipt.get('found')), 'reviewer': actor})
                return {'request_id': body['request_id'], 'receipt': receipt,
                        'automatic_retry': False,
                        'note': 'No receipt does not prove non-execution while a call may still be in flight.'}
            if path == '/v1/task-control':
                fields(body, {'task_id', 'operation'})
                if body['operation'] not in {'pause', 'resume', 'revoke', 'close_task'}:
                    raise APIError(400, 'invalid task operation')
                getattr(LifecycleOperator(store, registry), body['operation'])(body['task_id'])
                return {'task_id': body['task_id'], 'operation': body['operation'], 'acknowledged': True}
            if path == '/v1/evidence':
                fields(body, set())
                snapshot = store.snapshot()
                # Omit read results and submitted content from default export.
                for row in snapshot['requests']:
                    row['outcome'] = '[redacted]' if row['outcome'] else None
                for row in snapshot['approvals']:
                    proposed = row.pop('request', None)
                    row['request_digest'] = digest(proposed) if proposed else None
                attempts = snapshot['attempts']
                reasons = {}
                for row in attempts:
                    reasons[row['reason_code']] = reasons.get(row['reason_code'], 0) + 1
                return {'schema_version': 1, 'scope': 'local synthetic pilot', 'content_redacted': True,
                        'integrity': store.verify_event_chain(), 'state': snapshot,
                        'metrics': {'attempts': len(attempts), 'decisions_by_reason': reasons,
                                    'note': 'Attempts include approval holds and retries; these are not attack-effectiveness rates.'}}
            raise APIError(404, 'unknown API route')

    return Server((host, port), GatewayHandler)
