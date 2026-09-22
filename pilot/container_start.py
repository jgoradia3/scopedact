"""Copy read-only Docker secrets, prepare owned state, then permanently drop UID."""
import os
from pathlib import Path
import sys
uid = gid = 10001
private = Path('/run/private')
private.mkdir(mode=0o700, exist_ok=True)
os.chmod(private, 0o700)
for role in ('agent', 'child', 'operator', 'tool'):
    source = Path('/run/secrets') / (role + '.key')
    if source.is_file():
        target = private / (role + '.key')
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(source.read_bytes())
        os.chown(target, uid, gid)
        os.environ[f'SCOPEDACT_{role.upper()}_KEY_FILE'] = str(target)
os.chown(private, uid, gid)
state = Path('/state')
if os.environ.get("SCOPEDACT_DATABASE") and state.exists():
    os.chown(state, uid, gid)
os.setgroups([])
os.setgid(gid)
os.setuid(uid)
if os.environ.get("SCOPEDACT_DATABASE") and state.exists():
    os.chmod(state, 0o700)
os.execv(sys.executable, [sys.executable, '-m', 'scopedact.pilot', *sys.argv[1:]])
