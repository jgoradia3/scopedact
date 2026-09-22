"""Check both service-name and direct-IP isolation, not only Docker DNS."""
import ipaddress
import json
import subprocess

compose = ['docker', 'compose', '-f', 'compose.pilot.yaml']
identifier = subprocess.check_output(compose + ['ps', '-q', 'ticket-api'], text=True).strip()
if not identifier:
    raise SystemExit('Start the pilot before testing isolation')
networks = json.loads(subprocess.check_output(
    ['docker', 'inspect', '--format', '{{json .NetworkSettings.Networks}}', identifier], text=True))
if len(networks) != 1:
    raise SystemExit('Ticket service unexpectedly shares additional networks')
address = str(ipaddress.ip_address(next(iter(networks.values()))['IPAddress']))
for service in ('agent-probe','child-probe'):
    subprocess.run(compose + ['run','--rm','-e','SCOPEDACT_PROBE_TOOL_IP='+address,service],check=True)
