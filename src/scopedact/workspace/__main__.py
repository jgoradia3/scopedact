"""Local workspace operator CLI and reproducible, explicitly scripted agent client."""
import argparse
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4

from ..pilot.client import Client
from ..pilot.common import AGENT, CHILD, OPERATOR, secret_file
from .store import DocumentStore


def call(client, path, body):
    status, result = client.post(path,body)
    if status >= 400: raise RuntimeError(f'{status}: {result}')
    return result


def main():
    parser = argparse.ArgumentParser(description='ScopedAct managed workspace and task activity map')
    parser.add_argument('--directory', default='.scopedact-workspace')
    parser.add_argument('--url', default='http://127.0.0.1:8890')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    serve = sub.add_parser('serve'); serve.add_argument('--port',type=int,default=8890)
    serve.add_argument('--container',action='store_true',help='bind container interface; publish only on host loopback')
    imp = sub.add_parser('import'); imp.add_argument('file'); imp.add_argument('--name',required=True)
    exp = sub.add_parser('export-document'); exp.add_argument('--resource',required=True)
    exp.add_argument('--version',type=int,help='optional historical version')
    demo = sub.add_parser('demo'); demo.add_argument('--reads',type=int,default=4)
    sub.add_parser('resume-demo'); sub.add_parser('probe-demo')
    task = sub.add_parser('create-task', help='Operator creates explicit authority for a separate agent process')
    task.add_argument('--summary', required=True)
    task.add_argument('--read', action='append', default=[])
    task.add_argument('--update', action='append', default=[])
    task.add_argument('--lifetime', type=int, default=900)
    args = parser.parse_args(); root = Path(args.directory)
    if args.command == 'init':
        root.mkdir(mode=0o700,parents=True,exist_ok=True)
        secrets_dir = root/'secrets'; secrets_dir.mkdir(mode=0o700,exist_ok=True)
        if any(secrets_dir.iterdir()) or (root/'documents.db').exists():
            raise ValueError('workspace already exists; refusing to overwrite')
        for role in ('agent','child','operator'):
            fd=os.open(secrets_dir/f'{role}.key',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f: f.write(secrets.token_urlsafe(48)+'\n')
        docs=DocumentStore(root/'documents.db')
        for name,text in [('runbook.md','# Login troubleshooting\n\nCheck service health before making changes.\n'),
                          ('diagnostics.md','# Diagnostic notes\n\nA stale session can cause repeated login failures.\n'),
                          ('unassigned.md','# Separate assignment\n\nThis document is outside the demo task.\n')]:
            docs.import_text('doc:'+name,text)
        print(f'Initialized {root}. Operator console login file: {secrets_dir / "operator.key"}')
        return
    if not (root/'documents.db').is_file(): raise ValueError('run init first')
    docs = DocumentStore(root/'documents.db')
    if args.command == 'import':
        # Explicit operator import; no agent-supplied path is opened by the gateway.
        path=Path(args.file)
        if path.is_symlink() or not path.is_file(): raise ValueError('import requires a regular text file')
        with path.open('rb') as f: raw=f.read(8001)
        if len(raw)>8000: raise ValueError('document exceeds 8000 bytes')
        docs.import_text('doc:'+args.name,raw.decode('utf-8'))
        print('Imported a copy; the original file will not be edited.'); return
    if args.command == 'export-document':
        if args.version is None: text=docs.read(args.resource)['text']
        else:
            from contextlib import closing
            with closing(docs.connect()) as db:
                row=db.execute('SELECT text FROM document_versions WHERE resource=? AND version=?',(args.resource,args.version)).fetchone()
            if row is None: raise ValueError('version not found')
            text=row[0]
        print(text,end=''); return
    def key(role): return secret_file(root/'secrets'/f'{role}.key')
    if args.command == 'serve':
        from .server import build_workspace
        server=build_workspace('0.0.0.0' if args.container else '127.0.0.1',args.port,
            database=root/'gateway.db',documents=docs,agent_key=key('agent'),child_key=key('child'),operator_key=key('operator'))
        print(f'Console: http://127.0.0.1:{server.server_port} — open operator.key in the login screen.',flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()
        return
    if args.command == 'create-task':
        operator = Client(args.url, OPERATOR, key('operator'))
        permissions = [{'action': action, 'resource': resource}
                       for action in ('read', 'update') for resource in getattr(args, action)]
        print(json.dumps(call(operator, '/v1/tasks', {'summary': args.summary,
            'permissions': permissions, 'lifetime_seconds': args.lifetime}), indent=2))
        return
    parent=Client(args.url,AGENT,key('agent')); child=Client(args.url,CHILD,key('child'))
    saved=root/'demo.json'
    if args.command == 'demo':
        if not 1 <= args.reads <= 200: raise ValueError('reads must be 1–200')
        operator=Client(args.url,OPERATOR,key('operator'))
        permissions=[{'action':'read','resource':'doc:diagnostics.md'},
                     {'action':'read','resource':'doc:runbook.md'},{'action':'update','resource':'doc:runbook.md'}]
        task=call(operator,'/v1/tasks',{'summary':'Investigate login failures and propose a runbook update','permissions':permissions})['task_id']
        helper=call(parent,'/v1/delegations',{'parent_task_id':task,'permissions':[permissions[0]],'lifetime_seconds':300})['task_id']
        def action(client,task,resource):
            return call(client,'/v1/actions',{'task_id':task,'request_id':'request:'+uuid4().hex,'action':'read','resource':resource})
        runbook=action(parent,task,'doc:runbook.md')['value']
        for _ in range(args.reads): action(child,helper,'doc:diagnostics.md')
        blocked=action(child,helper,'doc:unassigned.md')
        assert blocked['decision']=='PERMISSION_NOT_GRANTED' and not blocked['executed']
        proposal={'task_id':task,'request_id':'request:'+uuid4().hex,'action':'update','resource':'doc:runbook.md',
                  'input':{'text':runbook['text']+'\nCheck for stale sessions; ask the customer to sign in again.\n','expected_version':runbook['version']}}
        result=call(parent,'/v1/actions',proposal)
        assert result['decision']=='APPROVAL_REQUIRED' and not result['executed']
        saved.write_text(json.dumps({'task_id':task,'child_task_id':helper,'proposal':proposal},indent=2)+'\n')
        saved.chmod(0o600)
        print(json.dumps({'task_id':task,'request_id':proposal['request_id'],'next':'Refresh console, inspect map and review exact proposal. Then run resume-demo.','scripted_clients':True},indent=2))
    elif args.command == 'resume-demo':
        data=json.loads(saved.read_text()); print(json.dumps(call(parent,'/v1/actions',data['proposal']),indent=2))
    else:
        data=json.loads(saved.read_text())
        print(json.dumps(call(child,'/v1/actions',{'task_id':data['child_task_id'],'request_id':'request:'+uuid4().hex,
            'action':'read','resource':'doc:diagnostics.md'}),indent=2))


if __name__=='__main__': main()
