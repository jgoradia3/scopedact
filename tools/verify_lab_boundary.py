"""Run inside the agent container. Deliberate boundary probes, not model behavior."""
import os
from pathlib import Path
import socket
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, secret_file

for path in ['/run/operator.key','/run/portal.key','/run/signing.key','/run/operations.key',
             '/run/reviewer-control.key','/run/child.key','/var/run/docker.sock','/state/portal.db','/state/gateway.db']:
    assert not Path(path).exists(), f'agent can see forbidden mount: {path}'
for name in ['identity','portal','operations','scenario']:
    try:
        with socket.create_connection((name,8080),timeout=.5):
            raise AssertionError(f'agent reached backend {name}')
    except (OSError,socket.timeout):pass
# CI/operator can supply concrete backend IPs to test routing as well as DNS separation.
for address in os.environ.get('LAB_BACKEND_IPS','').split(','):
    if not address:continue
    try:
        with socket.create_connection((address,8080),timeout=.5):
            raise AssertionError(f'agent reached backend IP {address}')
    except (OSError,socket.timeout):pass
client=Client('http://gateway:8891',AGENT,secret_file('/run/agent.key'))
for route in ['/v1/tasks','/v1/decision','/v1/task-control','/v1/map']:
    assert client.post(route,{})[0]==403, f'agent reached operator route {route}'
print('PASS: backend DNS/IP connections blocked; no privileged mounts; operator routes forbidden.')
