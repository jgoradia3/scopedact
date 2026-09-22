from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sys
from uuid import uuid4

from .common import AGENT, CHILD, OPERATOR, canonical, secret_file
from .client import Client


def main():
    parser = argparse.ArgumentParser(description='ScopedAct authenticated ticket pilot')
    parser.add_argument('--directory', default='.scopedact-pilot')
    parser.add_argument('--url', default=os.environ.get('SCOPEDACT_GATEWAY_URL', 'http://127.0.0.1:8870'))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    commands.add_parser('init-child')
    commands.add_parser('backend')
    commands.add_parser('gateway')
    probe = commands.add_parser('agent-probe')
    probe.add_argument('--role',choices=['agent','child'],default='agent')
    delegation = commands.add_parser('delegate')
    delegation.add_argument('--task-id',required=True)
    delegation.add_argument('--resource',default='ticket:T-100')
    delegation.add_argument('--actions',nargs='+',default=['read'])
    delegation.add_argument('--lifetime-seconds',type=int,default=300)
    lineage = commands.add_parser('lineage')
    lineage.add_argument('--task-id',required=True)
    lineage.add_argument('--json',action='store_true')
    create = commands.add_parser('create-task'); create.add_argument('--resource', default='ticket:T-100')
    invoke = commands.add_parser('invoke')
    invoke.add_argument('--task-id', required=True); invoke.add_argument('--request-id', default=None)
    invoke.add_argument('--action', required=True); invoke.add_argument('--resource', default='ticket:T-100')
    invoke.add_argument('--input-json')
    invoke.add_argument('--role',choices=['agent','child'],default='agent')
    for name in ('review', 'reconcile'):
        commands.add_parser(name).add_argument('--request-id', required=True)
    decision = commands.add_parser('decide')
    decision.add_argument('--request-id', required=True); decision.add_argument('--digest', required=True)
    choice = decision.add_mutually_exclusive_group(required=True)
    choice.add_argument('--approve', action='store_true'); choice.add_argument('--reject', action='store_true')
    control = commands.add_parser('control')
    control.add_argument('--task-id', required=True); control.add_argument('--operation', choices=['pause','resume','revoke','close_task'], required=True)
    for name in ('evaluate', 'evaluate-delegation', 'export'):
        commands.add_parser(name).add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.directory)
    def key(role):
        return secret_file(os.environ.get(f'SCOPEDACT_{role.upper()}_KEY_FILE', root / 'secrets' / f'{role}.key'))
    def save(value):
        path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + '\n')
        print(f'Saved {path}')
    if args.command in {'init','init-child'}:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = root / 'secrets'
        directory.mkdir(mode=0o700, exist_ok=True)
        if args.command == 'init':
            if any(directory.iterdir()):
                raise ValueError('refusing to overwrite existing secrets; use init-child to upgrade v0.13')
            roles = ('agent','child','operator','tool')
        else:
            for role in ('agent','operator','tool'):
                secret_file(directory / f'{role}.key')
            roles = ('child',)
        for role in roles:
            descriptor = os.open(directory / f'{role}.key', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(secrets.token_urlsafe(48) + '\n')
        print('Created separate secret files. Give each agent only its own key; keep operator/tool keys private.')
        return
    if args.command in {'backend', 'gateway'}:
        from .backend import build_backend
        from .connector import TicketRestConnector
        from .gateway import build_gateway
        host = os.environ.get('SCOPEDACT_BIND', '127.0.0.1')
        if args.command == 'backend':
            server = build_backend(host, int(os.environ.get('SCOPEDACT_PORT', '8881')),
                database=os.environ.get('SCOPEDACT_DATABASE', root / 'tickets.db'), key=key('tool'))
        else:
            tool, agent, operator, child = key('tool'), key('agent'), key('operator'), key('child')
            if len({tool, agent, operator, child}) != 4:
                raise ValueError('all four roles require distinct secrets')
            connector = TicketRestConnector(os.environ.get('SCOPEDACT_TICKET_URL', 'http://127.0.0.1:8881'), tool,
                allow_local_http=os.environ.get('SCOPEDACT_ALLOW_LOCAL_HTTP') == '1')
            connector.health()
            server = build_gateway(host, int(os.environ.get('SCOPEDACT_PORT', '8870')),
                database=os.environ.get('SCOPEDACT_DATABASE', root / 'gateway.db'), agent_key=agent,
                operator_key=operator, child_key=child, connector=connector)
        print(f'{args.command} listening on {host}:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    if args.command == 'agent-probe':
        agent = Client(args.url, CHILD if args.role=='child' else AGENT, key(args.role))
        status, _ = agent.post('/v1/tasks', {'resource':'ticket:T-200'})
        if status != 403:
            raise AssertionError('agent reached operator API')
        targets = ['ticket-api']
        if os.environ.get('SCOPEDACT_PROBE_TOOL_IP'):
            import ipaddress
            targets.append(str(ipaddress.ip_address(os.environ['SCOPEDACT_PROBE_TOOL_IP'])))
        for target in targets:
            try:
                connection = socket.create_connection((target, 8881), timeout=2)
            except OSError:
                pass
            else:
                connection.close()
                raise AssertionError('agent can reach protected network')
        print(f'PASS operator API denied; protected network unreachable via {len(targets)} target(s)')
        return
    if args.command in {'evaluate','evaluate-delegation'}:
        from .evaluate import evaluate
        from .evaluate_delegation import evaluate_delegation
        result = (evaluate_delegation(args.url,key('agent'),key('child'),key('operator'))
                  if args.command=='evaluate-delegation' else evaluate(args.url,key('agent'),key('operator')))
        save(result); print(f"PASS {result['passed']}/{result['total']} checks")
        return
    role = args.role if args.command=='invoke' else 'agent' if args.command=='delegate' else 'operator'
    client = Client(args.url, {'agent':AGENT,'child':CHILD,'operator':OPERATOR}[role], key(role))
    if args.command == 'create-task':
        path, body = '/v1/tasks', {'resource':args.resource}
    elif args.command == 'delegate':
        path,body='/v1/delegations',{'parent_task_id':args.task_id,
            'permissions':[{'action':action,'resource':args.resource} for action in args.actions],
            'lifetime_seconds':args.lifetime_seconds}
    elif args.command == 'lineage':
        path,body='/v1/lineage',{'task_id':args.task_id}
    elif args.command == 'invoke':
        path = '/v1/actions'
        body = {'task_id':args.task_id, 'request_id':args.request_id or 'request:'+uuid4().hex,
                'action':args.action, 'resource':args.resource}
        if args.input_json is not None: body['input'] = json.loads(args.input_json)
    elif args.command in {'review','reconcile'}:
        path, body = '/v1/'+args.command, {'request_id':args.request_id}
    elif args.command == 'decide':
        path, body = '/v1/decision', {'request_id':args.request_id,'digest':args.digest,'approve':args.approve}
    elif args.command == 'control':
        path, body = '/v1/task-control', {'task_id':args.task_id,'operation':args.operation}
    else:
        path, body = '/v1/evidence', {}
    status, result = client.post(path, body)
    if args.command == 'lineage' and status==200 and not args.json:
        from .delegation import render_lineage
        print(render_lineage(result))
    elif args.command == 'export' and status == 200: save(result)
    else: print(json.dumps({'http_status':status,**result},indent=2))
    if status >= 400: raise SystemExit(1)


if __name__ == '__main__':
    main()
