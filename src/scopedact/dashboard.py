from __future__ import annotations

import html, json, secrets
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .grants import SQLiteGrantRegistry
from .lifecycle import LifecycleOperator, LifecycleStore

STYLE=""":root{color-scheme:dark;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;background:#080d1b;color:#eef3ff}header{padding:24px 5vw 18px;border-bottom:1px solid #26314f;background:#101831}h1{margin:0}header p,.muted,.empty{color:#9eabc8}main{padding:22px 5vw 48px;display:grid;gap:20px}.cards{display:grid;grid-template-columns:repeat(5,minmax(130px,1fr));gap:10px}.card,section{background:#121b34;border:1px solid #26314f;border-radius:12px;padding:15px}.number{font-size:27px;font-weight:750;color:#76e6b5}.label{color:#aebbd8;font-size:13px}h2{margin-top:0;font-size:18px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:9px;border-bottom:1px solid #26314f;vertical-align:top}th{color:#9fb2d9}.badge,.chip{display:inline-block;border:1px solid #344467;border-radius:999px;padding:2px 8px;margin:2px;font-size:12px}.allow,.active,.approved,.healthy{color:#76e6b5}.deny,.revoked,.rejected,.error{color:#ff8f9c}.paused,.pending,.awaiting{color:#ffd479}.closed,.blocked{color:#b8c0d4}button{background:#243659;color:#eef3ff;border:1px solid #48618e;border-radius:7px;padding:6px 9px;margin:2px;cursor:pointer}button.danger{border-color:#9d4f5a}.toolbar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.timeline{display:grid;gap:8px}.event{border-left:3px solid #48618e;padding:7px 10px;background:#0e162c}code{color:#bcd3ff}.notice{padding:10px;border:1px solid #394b70;border-radius:8px;background:#0d162d}@media(max-width:950px){.cards{grid-template-columns:repeat(2,1fr)}section{overflow-x:auto}}"""

def _e(v): return html.escape(str(v if v is not None else ""))
def _short(v):
    text=str(v or ""); shown=text if len(text)<=25 else f"{text[:14]}…{text[-7:]}"
    return f'<code title="{_e(text)}">{_e(shown)}</code>'
def _time(v):
    try: return _e(datetime.fromisoformat(str(v).replace("Z","+00:00")).strftime("%Y-%m-%d %H:%M:%S UTC"))
    except ValueError: return _e(v)
def _badge(v):
    text=str(v or ""); return f'<span class="badge {_e(text.lower())}">{_e(text.replace("_"," "))}</span>'
def _task_table(rows):
    if not rows:return '<p class="empty">No tasks yet.</p>'
    body=[]
    for r in rows:
        buttons=[]
        if r["status"]=="active":buttons.append(("pause","Pause",""))
        if r["status"]=="paused":buttons.append(("resume","Resume",""))
        if r["status"] not in {"closed","revoked"}:buttons += [("revoke","Revoke","danger"),("close","Close","danger")]
        controls=''.join(f'<button class="{c}" data-task="{_e(r["task_id"])}" data-action="{a}">{label}</button>' for a,label,c in buttons)
        body.append(f'<tr><td>{_short(r["task_id"])}</td><td>{_short(r["initiator"])}</td><td>{_short(r["actor"])}</td><td>{_badge(r["status"])}</td><td>{_time(r["updated_at"])}</td><td>{controls}</td></tr>')
    return '<table><thead><tr><th>Task</th><th>Initiator</th><th>Agent</th><th>Status</th><th>Updated</th><th>Controls</th></tr></thead><tbody>'+''.join(body)+'</tbody></table>'
def _grants(rows):
    if not rows:return '<p class="empty">No grants yet.</p>'
    body=[]
    for r in rows:
        chips=''.join(f'<span class="chip">{_e(x.strip())}</span>' for x in r["permissions"].split(","))
        body.append(f'<tr><td>{_short(r["task_id"])}</td><td>{_short(r["principal"])}</td><td>{chips}</td><td>{_time(r["expires_at"])}</td><td>{"Yes" if r["revoked"] else "No"}</td></tr>')
    return '<table><thead><tr><th>Task</th><th>Principal</th><th>Exact permissions</th><th>Expires</th><th>Revoked</th></tr></thead><tbody>'+''.join(body)+'</tbody></table>'
def _attempts(rows):
    if not rows:return '<p class="empty">No attempts yet.</p>'
    body=[]
    for r in rows:
        reason=r["reason_code"]; cat="allowed" if r["decision"]=="allow" else ("awaiting" if reason=="APPROVAL_REQUIRED" else ("blocked" if reason=="TASK_NOT_ACTIVE" else "denied"))
        body.append(f'<tr data-category="{cat}"><td>{_short(r["request_id"])}</td><td>{_short(r["task_id"])}</td><td>{_e(r["action"])}</td><td>{_e(r["resource"])}</td><td>{_badge(r["decision"])}</td><td>{_badge(reason)}</td><td>{"Yes" if r["executed"] else "No"}</td></tr>')
    bar='<div class="toolbar">'+''.join(f'<button data-filter="{x}">{label}</button>' for x,label in [("all","All"),("allowed","Allowed"),("denied","Security denied"),("awaiting","Awaiting approval"),("blocked","Task-state blocked")])+'</div>'
    return bar+'<table id="attempts"><thead><tr><th>Request</th><th>Task</th><th>Action</th><th>Resource</th><th>Decision</th><th>Reason</th><th>Executed</th></tr></thead><tbody>'+''.join(body)+'</tbody></table>'
def _approvals(rows):
    if not rows:
        return '<p class="empty">No approval requests yet.</p>'
    body = []
    for row in rows:
        request = row.get("request")
        detail = ('<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'
                  + _e(json.dumps(request, indent=2, ensure_ascii=False)) + '</pre>') if request else (
                      '<p>Legacy request: full content unavailable. Reissue before approval.</p>')
        controls = ''
        if row['status'] == 'pending' and request:
            controls = (f'<button data-request="{_e(row["request_id"])}" data-approval="approve">Approve exact request</button>'
                        f'<button class="danger" data-request="{_e(row["request_id"])}" data-approval="reject">Reject</button>')
        body.append(f'<tr><td>{_short(row["request_id"])}</td><td>{detail}</td>'
                    f'<td>{_badge(row["status"])}</td><td>{_short(row["reviewer"])}</td>'
                    f'<td>{controls}</td></tr>')
    return ('<p>Review the exact task, actor, tool, resource, and input below. '
            'Append writes this content to the named file. Approval does not override task permissions or revocation.</p>'
            '<table><thead><tr><th>Request</th><th>Exact operation and input</th><th>Status</th>'
            '<th>Reviewer</th><th>Decision</th></tr></thead><tbody>' + ''.join(body) + '</tbody></table>')

def _executions(rows):
    if not rows:
        return '<p class="empty">No execution claims yet.</p>'
    return ('<p>Evaluating may mean in progress or interrupted. Unknown means the effect must '
            'be checked manually. Neither state is automatically retried.</p><table>'
            '<thead><tr><th>Request</th><th>Execution state</th></tr></thead><tbody>'
            + ''.join(f'<tr><td>{_short(row["request_id"])}</td><td>{_badge(row["state"])}</td></tr>'
                      for row in rows) + '</tbody></table>')

def _events(rows):
    output=[]
    for r in rows[:100]:
        try: details=json.loads(r["details"])
        except (ValueError,TypeError):details={"details":r["details"]}
        chips=''.join(f'<span class="chip"><b>{_e(k)}</b>: {_e(v)}</span>' for k,v in details.items())
        output.append(f'<div class="event"><b>{_e(r["event_type"].replace("_"," ").title())}</b> <span class="muted">{_time(r["timestamp"])}</span><br>{_short(r["task_id"])} {chips}</div>')
    return '<div class="timeline">'+''.join(output)+'</div>' if output else '<p class="empty">No events yet.</p>'

def render_dashboard(snapshot,csrf_token="",script_nonce=""):
    tasks=snapshot.get("tasks",[]); attempts=snapshot.get("attempts",[]); approvals=snapshot.get("approvals",[]); active=sum(r["status"]=="active" for r in tasks)
    allowed=sum(r["decision"]=="allow" for r in attempts); security=sum(r["decision"]=="deny" and r["reason_code"] not in {"APPROVAL_REQUIRED","TASK_NOT_ACTIVE"} for r in attempts); pending=sum(r["status"]=="pending" for r in approvals); blocked=sum(r["reason_code"]=="TASK_NOT_ACTIVE" for r in attempts)
    integrity=snapshot.get("integrity",{"valid":True,"events":len(snapshot.get("events",[]))}); connectors=snapshot.get("connectors",[])
    connector_html='<p class="empty">No connector preflight recorded.</p>' if not connectors else ''.join(f'<div>{_badge(r["status"])} <b>{_e(r["name"])}</b> <span class="muted">{_time(r["updated_at"])}</span></div>' for r in connectors)
    meaning='<div class="notice"><b>How to read this console</b><p><b>Proposal</b>: an agent asked to act. <b>Decision</b>: ScopedAct evaluated that request. <b>Executed: Yes</b>: the protected tool was actually called. <b>Awaiting approval</b>: the request was processed but the tool was not called.</p></div>'
    note=meaning+('' if active else '<div class="notice"><b>Create an agent task</b><p>Load the configured initiator, agent, exact permissions, approval policy, and grant lifetime from the project lifecycle policy.</p><button data-create="default">Review and create task</button></div>')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="csrf-token" content="{_e(csrf_token)}"><title>ScopedAct Operator Console</title><style>{STYLE}</style></head><body><header><h1>ScopedAct Operator Console</h1><p>Local authority-lifecycle operations and evidence</p></header><main><div class="cards"><div class="card"><div class="number">{len(tasks)}</div><div class="label">Tasks</div></div><div class="card"><div class="number">{active}</div><div class="label">Active now</div></div><div class="card"><div class="number">{allowed}</div><div class="label">Allowed</div></div><div class="card"><div class="number">{security}</div><div class="label">Security denied</div></div><div class="card"><div class="number">{pending} / {blocked}</div><div class="label">Awaiting / state-blocked</div></div></div>{note}<section><h2>Tasks</h2>{_task_table(tasks)}</section><section><h2>Task grants</h2>{_grants(snapshot.get("grants",[]))}</section><section><h2>Action attempts</h2>{_attempts(attempts)}</section><section><h2>Execution claims</h2>{_executions(snapshot.get("executions",[]))}</section><section><h2>Approvals</h2>{_approvals(approvals)}</section><section><h2>Connector health</h2>{connector_html}</section><section><h2>Lifecycle timeline</h2><p>{_badge("healthy" if integrity.get("valid") else "error")} Event chain: {integrity.get("events",0)} events</p>{_events(snapshot.get("events",[]))}</section></main><script nonce="{_e(script_nonce)}">const token=document.querySelector('meta[name=csrf-token]').content;async function post(path,body){{if(!confirm('Apply this operator action?'))return;const r=await fetch(path,{{method:'POST',headers:{{'Content-Type':'application/json','X-ScopedAct-CSRF':token}},body:JSON.stringify(body)}});const x=await r.json();if(!r.ok)alert(x.error||'Action failed');else location.reload();}}document.addEventListener('click',e=>{{const b=e.target.closest('button');if(!b)return;if(b.dataset.filter){{document.querySelectorAll('#attempts tbody tr').forEach(r=>r.hidden=b.dataset.filter!=='all'&&r.dataset.category!==b.dataset.filter);return}}if(b.dataset.create)post('/api/task/create',{{template:'default'}});if(b.dataset.task)post('/api/task/'+b.dataset.action,{{task_id:b.dataset.task}});if(b.dataset.approval)post('/api/approval/'+b.dataset.approval,{{request_id:b.dataset.request,reviewer:'human:dashboard-reviewer'}});}});</script></body></html>'''

def apply_operator_action(database,path,payload,config_path="config/lifecycle.json"):
    routes={"/api/task/pause":"pause","/api/task/resume":"resume","/api/task/revoke":"revoke","/api/task/close":"close_task","/api/approval/approve":"approve","/api/approval/reject":"reject"}
    if path=="/api/task/create":
        if payload!={"template":"default"}:raise ValueError("task creation requires the default reviewed template")
        from .mvp import initialize_demo_task
        initialize_demo_task(database,config_path);return
    if path not in routes:raise ValueError("unsupported operator action")
    store=LifecycleStore(database); registry=SQLiteGrantRegistry(database); operator=LifecycleOperator(store,registry)
    try:
        if path.startswith("/api/task/"):
            if set(payload)!={"task_id"}:raise ValueError("task action requires task_id")
            getattr(operator,routes[path])(payload["task_id"])
        else:
            if set(payload)!={"request_id","reviewer"}:raise ValueError("approval action requires request_id and reviewer")
            getattr(operator,routes[path])(payload["request_id"],payload["reviewer"])
    finally:store.close(); registry.close()

def serve_dashboard(database,host="127.0.0.1",port=8765,config_path="config/lifecycle.json"):
    if host not in {"127.0.0.1","localhost","::1"}:raise ValueError("dashboard host must be a loopback address")
    database=str(database); csrf=secrets.token_urlsafe(32); nonce=secrets.token_urlsafe(20)
    class Handler(BaseHTTPRequestHandler):
        def headers_out(self,status,kind,body):
            self.send_response(status);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("Content-Security-Policy",f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; connect-src 'self'");self.send_header("Referrer-Policy","no-referrer");self.end_headers()
        def do_GET(self):
            path=urlparse(self.path).path
            if path not in {"/","/api/state"}:self.send_error(404);return
            store=LifecycleStore(database)
            try:snapshot=store.snapshot();snapshot["integrity"]=store.verify_event_chain()
            finally:store.close()
            body=(json.dumps(snapshot,sort_keys=True) if path=="/api/state" else render_dashboard(snapshot,csrf,nonce)).encode();self.headers_out(200,"application/json" if path=="/api/state" else "text/html; charset=utf-8",body);self.wfile.write(body)
        def do_POST(self):
            try:
                if not secrets.compare_digest(self.headers.get("X-ScopedAct-CSRF",""),csrf):raise PermissionError("invalid CSRF token")
                if self.headers.get_content_type()!="application/json":raise ValueError("JSON body required")
                size=int(self.headers.get("Content-Length","0"))
                if size<2 or size>8192:raise ValueError("invalid body size")
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError("JSON object required")
                apply_operator_action(database,urlparse(self.path).path,payload,config_path);result={"ok":True};status=200
            except PermissionError as error:result={"error":str(error)};status=403
            except (ValueError,json.JSONDecodeError) as error:result={"error":str(error)};status=400
            body=json.dumps(result).encode();self.headers_out(status,"application/json",body);self.wfile.write(body)
        def log_message(self,format,*args):return
    server=ThreadingHTTPServer((host,port),Handler);print(f"ScopedAct dashboard: http://{host}:{port}");print("Local operator console. Press Ctrl+C to stop.")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
