"""Run inside the declared agent container, which has only its role key."""
import os
from pathlib import Path
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD

role=CHILD if os.environ['SCOPEDACT_AGENT_ROLE']=='child' else AGENT
client=Client('http://gateway:8890',role,Path('/run/agent.key').read_text().strip())
for route in ['/v1/workspace','/v1/map','/v1/tasks','/v1/decision','/v1/task-control','/v1/document-review']:
    assert client.post(route,{})[0]==403,route
for path in ['/state/documents.db','/state/gateway.db','/state/secrets/operator.key','/var/run/docker.sock']:
    assert not Path(path).exists(),path
print('PASS: '+role+' cannot access operator APIs, managed storage, operator secret, or Docker socket in this deployment.')
