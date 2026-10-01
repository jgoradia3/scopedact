"""Run a fresh synthetic pilot and render read-only documentation for screenshots.

This is a trusted scenario harness, not an agent runtime or an operator UI.
No keys or databases are exported; the temporary services bind only to loopback.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import argparse
import html
import json
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import threading

from scopedact import __version__
from scopedact.pilot.backend import build_backend, TicketStore
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD, OPERATOR
from scopedact.pilot.connector import TicketRestConnector
from scopedact.pilot.gateway import build_gateway


def run_demo():
    with TemporaryDirectory(prefix='scopedact-demo-') as directory, ExitStack() as stack:
        root = Path(directory)
        keys = {role: secrets.token_urlsafe(48) for role in ('agent', 'child', 'operator', 'tool')}
        backend = build_backend('127.0.0.1', 0, database=root/'tickets.db', key=keys['tool'])
        def start(server):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def stop():
                server.shutdown(); server.server_close(); thread.join()
            stack.callback(stop)
        start(backend)
        connector = TicketRestConnector(f'http://127.0.0.1:{backend.server_port}', keys['tool'], allow_local_http=True)
        gateway = build_gateway('127.0.0.1', 0, database=root/'gateway.db', agent_key=keys['agent'],
                                child_key=keys['child'], operator_key=keys['operator'], connector=connector)
        start(gateway)
        url = f'http://127.0.0.1:{gateway.server_port}'
        parent, child, operator = (Client(url, identity, keys[key]) for identity, key in
                                  ((AGENT, 'agent'), (CHILD, 'child'), (OPERATOR, 'operator')))
        calls = []
        def post(client, path, body):
            status, response = client.post(path, body)
            if status != 200:
                raise RuntimeError(f'{path}: HTTP {status}: {response}')
            calls.append({'path':path, 'response':response})
            return response
        task = post(operator, '/v1/tasks', {'resource':'ticket:T-100'})['task_id']
        grant = post(parent, '/v1/delegations', {'parent_task_id':task,
                     'permissions':[{'action':'read','resource':'ticket:T-100'}], 'lifetime_seconds':300})
        def action(task_id, request, verb, resource='ticket:T-100', **extra):
            return {'task_id':task_id, 'request_id':'request:'+request, 'action':verb, 'resource':resource, **extra}
        read = post(child, '/v1/actions', action(grant['task_id'], 'demo-read', 'read'))
        denied = post(child, '/v1/actions', action(grant['task_id'], 'demo-blocked', 'read', 'ticket:T-200'))
        proposal = action(task, 'demo-update', 'update', input={'text':'Investigated login issue; next step is a password reset.', 'expected_version':1})
        held = post(parent, '/v1/actions', proposal)
        store = TicketStore(root/'tickets.db')
        before = store.read('T-100')
        review = post(operator, '/v1/review', {'request_id':proposal['request_id']})
        post(operator, '/v1/decision', {'request_id':proposal['request_id'], 'digest':review['digest'], 'approve':True})
        approved = post(parent, '/v1/actions', proposal)
        after = store.read('T-100')
        post(operator, '/v1/task-control', {'task_id':task, 'operation':'revoke'})
        revoked = post(child, '/v1/actions', action(grant['task_id'], 'demo-after-revoke', 'read'))
        lineage = post(operator, '/v1/lineage', {'task_id':task})
        assert read['executed'] and read['decision']=='PERMISSION_GRANTED'
        assert not denied['executed'] and denied['decision']=='PERMISSION_NOT_GRANTED'
        assert not held['executed'] and held['decision']=='APPROVAL_REQUIRED' and before['comments']==[]
        assert approved['executed'] and after['version']==2 and len(after['comments'])==1
        assert not revoked['executed'] and revoked['decision']=='ANCESTOR_INACTIVE'
        # Whitelisted response excerpts: no keys, full generated IDs, or database exports.
        def result(response):
            return {key:response[key] for key in ('decision','executed')}
        return {'version':__version__, 'captured_at':datetime.now(timezone.utc).isoformat(),
                'read':result(read), 'denied':result(denied), 'held':result(held), 'approved':result(approved),
                'revoked':result(revoked), 'proposal_text':review['request']['input']['text'],
                'ticket_version_before':before['version'], 'ticket_version_after':after['version'],
                'initiator':lineage['initiator'], 'parent':AGENT, 'child':CHILD,
                'child_permissions':grant['permissions'],
                'actions':[{key:event[key] for key in ('actor','action','resource','tool','decision','outcome')}
                           for event in lineage['actions']]}


CSS = '''
*{box-sizing:border-box}body{margin:0;background:#edf1f5;color:#142334;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1200px;margin:auto;padding:24px 44px 20px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #cbd6df;padding-bottom:18px}
.brand{font-size:22px;font-weight:800;letter-spacing:-.8px}.brand span{color:#087e83}.meta{font-size:12px;letter-spacing:.8px;color:#516778;text-transform:uppercase}
h1{font-size:36px;line-height:1.1;letter-spacing:-1.7px;margin:18px 0 10px}p{line-height:1.5;color:#516778;margin:0 0 22px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:white;border:1px solid #d3dee6;border-radius:12px;overflow:hidden}
.top{padding:12px 22px 6px;display:flex;align-items:center;justify-content:space-between}.step{font-size:12px;letter-spacing:1.3px;color:#61798b;font-weight:700}
.badge{border-radius:30px;background:#ddf5eb;color:#12603f;font-weight:750;font-size:12px;padding:6px 10px}.blocked{background:#ffe6e2;color:#9c3326}.held{background:#fff1cc;color:#805700}
h2{font-size:20px;letter-spacing:-.5px;margin:0 22px 6px}.card p{font-size:14px;margin:0 22px 12px;min-height:38px}
pre{background:#102334;color:#e1eef5;margin:0;padding:12px 22px;font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
footer{margin-top:16px;color:#526a7b;font-size:12px;line-height:1.6}.chain{display:flex;gap:12px;align-items:center;margin:22px 0}.node{flex:1;background:white;border:1px solid #d3dee6;padding:17px;border-radius:10px}.node small{display:block;color:#61798b;margin-bottom:8px}.node b{font-size:15px}.arrow{color:#087e83;font-size:24px}
table{width:100%;border-collapse:collapse;background:white;border:1px solid #d3dee6;font-size:14px}th{text-align:left;background:#102334;color:#e1eef5;padding:14px}td{padding:13px;border-bottom:1px solid #e0e7ed}td:nth-child(4){font:12px ui-monospace,SFMono-Regular,Menlo,monospace}.note{padding:18px 22px;background:#fff1cc;border:1px solid #ead59d;border-radius:10px;margin-top:20px;font-size:15px}.note b{display:block;margin-bottom:5px}
@media(max-width:760px){main{padding:24px}.grid{grid-template-columns:1fr}h1{font-size:32px}.chain{flex-direction:column}.node{width:100%}table{font-size:12px}th,td{padding:8px}}
'''


def render(data, output):
    output.mkdir(parents=True, exist_ok=True)
    e = html.escape
    def page(title, body):
        return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)} | ScopedAct recorded demo</title><style>{CSS}</style><main><header><div class="brand">Scoped<span>Act</span></div><div class="meta">Recorded demo · Synthetic tickets · Actual API results</div></header>{body}<footer>Documentation viewer, not an operator dashboard. Scripted clients; real loopback HTTP calls.<br>ScopedAct {e(data['version'])} · Source: tools/build_demo_report.py · No company data or credentials shown.</footer></main></html>'''
    def card(number, title, desc, label, kind, response, extra=''):
        excerpt=json.dumps(response,indent=2)
        return f'<section class="card"><div class="top"><span class="step">{number}</span><span class="badge {kind}">{label}</span></div><h2>{title}</h2><p>{desc}</p><pre>{e(excerpt+extra)}</pre></section>'
    cards = card('01 / ASSIGNED WORK','Read the assigned ticket','The diagnostic child reads T-100 using its read-only grant.','ALLOWED','',data['read'])
    cards += card('02 / OUTSIDE THE TASK','Another ticket? Access denied.','The same child asks for T-200. Its task does not grant access.','BLOCKED','blocked',data['denied'])
    cards += card('03 / SENSITIVE CHANGE','Wait for the operator','The primary proposes a comment. The ticket stays unchanged.','APPROVAL REQUIRED','held',data['held'])
    cards += card('04 / EXACT PROPOSAL APPROVED','Execute the reviewed change','The operator approves its digest. The same request then executes.','EXECUTED','',data['approved'])
    body='<h1>One task. Clear boundaries.</h1><p>A support-ticket workflow showing what executes, what is blocked, and what needs approval.</p><div class="grid">'+cards+'</div>'
    (output/'index.html').write_text(page('Allow, deny, approve',body))
    chain=''.join(f'<div class="node"><small>{label}</small><b>{e(data[key])}</b></div>'+('<span class="arrow">→</span>' if key!='child' else '') for label,key in [('Initiating operator','initiator'),('Primary agent','parent'),('Read-only child','child')])
    rows=''.join('<tr>'+''.join(f'<td>{e(str(event[key]))}</td>' for key in ('actor','action','resource','decision','outcome'))+'</tr>' for event in data['actions'])
    body='<h1>Follow the authority. See the outcome.</h1><p>One operator, one primary agent, one delegated child. Every row below comes from recorded lineage.</p><div class="chain">'+chain+'</div><table><thead><tr><th>Who acted</th><th>Action</th><th>Resource</th><th>Gateway decision</th><th>Outcome</th></tr></thead><tbody>'+rows+'</tbody></table><div class="note"><b>Parent authority revoked → next child action blocked</b>In-flight operations are not canceled or undone. These records show subsequent-action enforcement.</div>'
    (output/'lineage.html').write_text(page('Delegation and intervention',body))
    (output/'results.json').write_text(json.dumps(data,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('pilot-results/demo-report'))
    args=parser.parse_args()
    render(run_demo(),args.output)
    print(f'PASS: real read / deny / approval / execution / revocation; report saved to {args.output}')
