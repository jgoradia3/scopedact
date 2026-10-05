"""Same-origin operator console using the existing signed, role-separated API."""
from collections import Counter
from datetime import timedelta, datetime, timezone
import json
from pathlib import Path

from ..lifecycle import GrantIssuer, run_id
from ..models import Permission
from ..pilot.common import AGENT, OPERATOR
from ..pilot.delegation import lineage_report
from ..pilot.gateway import APIError, build_gateway, fields
from .discovery import search, searches, choose
from .store import DocumentConnector, document_id, validate_replacement

STATIC = Path(__file__).parent / 'static'


def activity_map(store, registry, task_id):
    report = lineage_report(store, registry, task_id)
    for node in report['nodes']:
        chain = [node]
        parent = node['parent_task_id']
        while parent:
            ancestor = next((n for n in report['nodes'] if n['task_id'] == parent), None)
            if ancestor is None: break
            chain.append(ancestor); parent = ancestor['parent_task_id']
        inactive = next((n for n in chain if n['grant_revoked'] or n['task_status'] != 'active'
                         or datetime.fromisoformat(n['expires_at']) <= datetime.now(timezone.utc)), None)
        node['effective_authority'] = 'inactive' if inactive else 'active'
        node['inactive_via'] = inactive['task_id'] if inactive else None
    groups = {}
    for event in report['actions']:
        key = (event['task_id'], event['actor'], event['tool'], event['resource'])
        group = groups.setdefault(key, {'task_id': key[0], 'actor': key[1], 'tool': key[2],
            'resource': key[3], 'count': 0, 'decisions': Counter(), 'events': []})
        group['count'] += 1
        group['decisions'][event['decision']] += 1
        group['events'].append(event)
    ids = {node['task_id'] for node in report['nodes']}
    timeline = []
    assignment=None
    for row in store.connection.execute('SELECT * FROM lifecycle_events ORDER BY event_id'):
        if row['task_id'] not in ids:
            continue
        details = json.loads(row['details'])
        if row['event_type']=='incident_scope_resolved' and row['task_id']==task_id:
            assignment={k:details[k] for k in ('incident','role','authority_source','policy_revision','permissions','excluded','lifetime_seconds','policy_name','limitations','scenario') if k in details}
        # Explicit metadata allowlist: never return prompt bodies or document content.
        safe = {k: details[k] for k in ('actor','action','resource','status','reviewer','approved',
                'reason_code','decision','outcome','category','receipt_found','passed','config_version','checked_at','reason') if k in details}
        timeline.append({'event_id': row['event_id'], 'timestamp': row['timestamp'],
            'type': row['event_type'], 'task_id': row['task_id'], 'request_id': row['request_id'], 'details': safe})
    requests = []
    for row in store.connection.execute('SELECT request_id,canonical,state FROM execution_claims'):
        proposal = json.loads(row['canonical'])
        if proposal['task_id'] in ids:
            status = store.approval_status(row['request_id'])
            requests.append({'request_id': row['request_id'], 'task_id': proposal['task_id'],
                'resource': proposal['resource'], 'action': proposal['action'], 'state': row['state'],
                'approval': status.value if status else None})
    return {**report, 'assignment':assignment, 'searches': [s for identifier in sorted(ids) for s in searches(store, identifier)], 'groups': list(groups.values()), 'timeline': timeline, 'requests': requests, 'verifications': [e for e in timeline if e['type']=='service_verification'],
        'integrity': store.verify_event_chain(),
        'coverage': 'Only authenticated requests through this gateway. No host-wide monitoring or live-model reasoning. Malformed/unauthenticated requests are not in the task map.',
        'counts': {'attempts': len(report['actions']),
            'completed': sum(e['outcome']=='succeeded' for e in report['actions']),
            'held': sum(e['decision']=='APPROVAL_REQUIRED' for e in report['actions']),
            'blocked': sum(e['outcome']=='not_dispatched' and e['decision']!='APPROVAL_REQUIRED' for e in report['actions']),
            'uncertain': sum(e['outcome']=='unknown' for e in report['actions'])}}


def investigation_progress(store, task_id):
    """Observed progress, independent of whether remaining authority is active."""
    claims=[r for r in store.connection.execute('SELECT canonical,state FROM execution_claims')
            if json.loads(r['canonical'])['task_id']==task_id]
    if any(r['state'] in {'unknown','evaluating'} for r in claims):return 'Outcome needs review'
    for r in claims:
        proposal=json.loads(r['canonical'])
        if r['state']=='pending' and proposal['action']=='update':
            status=store.approval_status(proposal['request_id'])
            if status and status.value=='approved':return 'Approved; not yet applied'
            if status and status.value=='pending':return 'Awaiting approval'
    events=store.connection.execute("SELECT event_type,details FROM lifecycle_events WHERE task_id=? AND event_type IN ('service_verification','attributed_action') ORDER BY event_id DESC",(task_id,))
    for row in events:
        details=json.loads(row['details'])
        if row['event_type']=='service_verification':
            return 'Recovery verified' if details.get('passed') else 'Verification failed'
        if details.get('action')=='update' and details.get('outcome')=='succeeded':return 'Change applied; verify recovery'
    if claims:return 'Activity recorded; inspect results'
    return 'No actions recorded'


def build_workspace(host, port, *, database, documents, agent_key, child_key, operator_key, console_sessions=None, guide=None):
    server = build_gateway(host, port, database=database, agent_key=agent_key, child_key=child_key,
        operator_key=operator_key, connector=DocumentConnector(documents),
        resource_validator=document_id, input_validator=validate_replacement, agent_routes=('/v1/document-search',), console_sessions=console_sessions)
    if guide:
        from ..lifecycle import LifecycleStore
        store=LifecycleStore(database)
        try:guide.initialize(store)
        finally:store.close()
    base = server.RequestHandlerClass

    class WorkspaceHandler(base):
        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{server.server_port}', f'localhost:{server.server_port}', f'gateway:{server.server_port}'}

        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self.valid_host() or (origin and origin != 'http://' + self.headers.get('Host','')):
                self.reply(403, {'error':'same-origin local access required'}); return
            if self.headers.get('X-ScopedAct-Console') == '1' and origin != 'http://' + self.headers.get('Host',''):
                self.reply(403, {'error':'Console requests require the same origin'}); return
            if console_sessions and self.path in {'/console/login','/console/logout','/console/restore'}:
                if origin != 'http://' + self.headers.get('Host','') or self.headers.get('X-ScopedAct-Console') != '1':
                    self.reply(403,{'error':'same-origin console request required'});return
                try:
                    _,body=self.body()
                    if self.path=='/console/login':
                        fields(body,{'code'});token,csrf=console_sessions.login(body['code'])
                        self.console_reply({'csrf':csrf},'scopedact_console='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600')
                    elif self.path=='/console/restore':
                        fields(body,set());self.reply(200,{'csrf':console_sessions.restore(self.headers)})
                    else:
                        fields(body,set());console_sessions.logout(self.headers)
                        self.console_reply({'signed_out':True},'scopedact_console=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                except PermissionError as error:self.reply(401,{'error':str(error)})
                except (ValueError,TypeError,KeyError):self.reply(400,{'error':'invalid sign-in request'})
                return
            super().do_POST()

        def console_reply(self,body,cookie):
            raw=json.dumps(body).encode();self.send_response(200)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('Set-Cookie',cookie)
            self.end_headers();self.wfile.write(raw)

        def do_GET(self):
            if not self.valid_host():
                self.reply(403, {'error': 'invalid host'}); return
            if self.path == '/console/config':
                self.reply(200,{'session_login':console_sessions is not None,'guided_lab':guide is not None});return
            assets = {'/': ('index.html','text/html'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css')}
            if self.path not in assets:
                return super().do_GET()
            name, mime = assets[self.path]
            raw = (STATIC / name).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers(); self.wfile.write(raw)

        def route(self, body, actor, store, registry):
            if guide and self.path.startswith('/v1/lab/'):
                return guide.route(self,body,actor,store,registry)
            if self.path == '/v1/document-search':
                return search(body,actor,store,registry,documents)
            if self.path == '/v1/document-choice':
                return choose(body,store,registry)
            if self.path == '/v1/tasks':
                fields(body, {'summary','permissions'}, {'lifetime_seconds'})
                summary = body['summary']
                if not isinstance(summary,str) or not 1 <= len(summary.strip()) <= 240:
                    raise APIError(400,'task summary must be 1–240 characters')
                values = body['permissions']
                if not isinstance(values,list) or not 1 <= len(values) <= 32:
                    raise APIError(400,'select 1–32 explicit permissions')
                catalog = {d['resource']: d.get('actions', ['read','update']) for d in documents.catalog()}
                for p in values:
                    if not isinstance(p,dict): raise APIError(400,'invalid permission')
                    fields(p, {'action','resource'})
                    document_id(p['resource'])
                    if p['resource'] not in catalog or p['action'] not in catalog[p['resource']]:
                        raise APIError(400,'unknown document or action')
                lifetime = body.get('lifetime_seconds',900)
                if type(lifetime) is not int or not 60 <= lifetime <= 3600:
                    raise APIError(400,'lifetime must be 60–3600 seconds')
                permissions = {Permission(**p) for p in values}
                store.add_authority(OPERATOR, permissions)
                identifier = run_id('task-workspace')
                GrantIssuer(store,registry).issue(task_id=identifier,initiator=OPERATOR,actor=AGENT,
                    permissions=permissions,lifetime=timedelta(seconds=lifetime))
                store.event('task_described',identifier,None,{'summary':summary.strip()})
                return {'task_id':identifier,'summary':summary.strip()}
            if self.path == '/v1/workspace':
                fields(body,set())
                roots = []
                for row in store.connection.execute('SELECT rowid AS sequence,body,revoked FROM grants ORDER BY rowid DESC'):
                    grant = json.loads(row['body'])
                    if grant['parent_task_id']: continue
                    task = store.get_task(grant['task_id'])
                    description = store.connection.execute("SELECT details FROM lifecycle_events WHERE task_id=? AND event_type='task_described' ORDER BY event_id DESC LIMIT 1",(grant['task_id'],)).fetchone()
                    roots.append({'task_id':grant['task_id'],'status':task.status.value,
                        'revoked':bool(row['revoked']), 'expires_at':grant['expires_at'],
                        'run_number':row['sequence'],
                        'created_at':store.connection.execute('SELECT MIN(timestamp) FROM lifecycle_events WHERE task_id=?',(grant['task_id'],)).fetchone()[0],
                        'progress':investigation_progress(store,grant['task_id']),
                        'summary':json.loads(description[0])['summary'] if description else 'Workspace task'})
                return {'tasks':roots,'documents':documents.catalog()}
            if self.path == '/v1/map':
                fields(body, {'task_id'})
                return activity_map(store,registry,body['task_id'])
            if self.path == '/v1/document-review':
                fields(body, {'request_id'})
                # Only stored proposals, never a caller-selected arbitrary document.
                row = store.connection.execute('SELECT canonical FROM execution_claims WHERE request_id=?',(body['request_id'],)).fetchone()
                if not row: raise APIError(404,'proposal not found')
                p = json.loads(row[0])
                if p['action'] != 'update': raise APIError(400,'not an update')
                return {'current':documents.read(p['resource'])}
            result = super().route(body,actor,store,registry)
            if self.path == '/v1/actions' and result.get('executed') and hasattr(documents, 'verification'):
                verification = documents.verification(body, result.get('value'))
                if verification:
                    store.event('service_verification', body['task_id'], body['request_id'], verification)
            if self.path == '/v1/evidence': result['scope'] = 'managed workspace; gateway-covered activity only'
            return result
    server.RequestHandlerClass = WorkspaceHandler
    return server
