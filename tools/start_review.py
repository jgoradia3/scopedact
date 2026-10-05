#!/usr/bin/env python3
"""One local command: prepare Docker services and open a one-time reviewer link."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Start the local ScopedAct reviewer experience')
parser.add_argument('--no-open',action='store_true',help='print the private sign-in link without opening a browser')
args=parser.parse_args()
os.chdir(root)
env={**os.environ,'PYTHONPATH':str(root/'src')}
# Linux bind mounts retain host ownership. Keep private modes and run as that owner.
if sys.platform.startswith('linux'):
    env.setdefault('SCOPEDACT_UID',str(os.getuid()))
    env.setdefault('SCOPEDACT_GID',str(os.getgid()))
docker=shutil.which('docker')
if not docker:sys.exit('Docker is required. Install and start Docker Desktop, then run this command again.')
def execute(command,**kwargs):return subprocess.run(command,check=True,env=env,**kwargs)
try:
    execute([docker,'info'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:sys.exit('Start Docker Desktop, then run this command again.')
state=root/'.scopedact-lab'
if not (state/'secrets').exists():execute([sys.executable,'-m','scopedact.incident_lab','init'])
# Upgrade existing lab state without overwriting credentials or evidence.
control=state/'secrets/reviewer-control.key'
if not control.exists():
    with control.open('x') as f:
        os.fchmod(f.fileno(),0o600);f.write(secrets.token_urlsafe(48)+'\n')
(state/'reviewer-journal').mkdir(mode=0o700,exist_ok=True)
compose=[docker,'compose','-p','scopedact-live-lab','-f','compose.lab.yaml']
print('Starting your local lab. First setup builds containers and downloads a local model.',flush=True)
# This setup-only model service has Internet access to download weights. No app keys are mounted.
volume=env.get('SCOPEDACT_MODEL_VOLUME','scopedact-lab-models')
execute([docker,'volume','create',volume],stdout=subprocess.DEVNULL)
loader='scopedact-review-loader-'+secrets.token_hex(4)
image='ollama/ollama@sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01'
execute([docker,'run','-d','--name',loader,'-v',volume+':/root/.ollama',image],stdout=subprocess.DEVNULL)
try:
    import time
    for _ in range(30):
        probe=subprocess.run([docker,'exec',loader,'ollama','list'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if probe.returncode==0:break
        time.sleep(1)
    else:raise RuntimeError('Local model loader did not start')
    available=subprocess.run([docker,'exec',loader,'ollama','show','qwen3:1.7b'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if available.returncode:execute([docker,'exec',loader,'ollama','pull','qwen3:1.7b'])
finally:
    subprocess.run([docker,'stop',loader],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([docker,'rm',loader],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
execute(compose+['up','--build','-d','--wait','identity','portal','operations','scenario','gateway','model','reviewer-worker'])
command=[sys.executable,'-m','scopedact.incident_lab','review']
if not args.no_open:command.append('--open')
execute(command)
