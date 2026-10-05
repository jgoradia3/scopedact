"""Short-lived local console sessions. No operator signing key enters the browser."""
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import secrets
import threading
import time

from ..pilot.common import OPERATOR


def issue_access(directory):
    """Called by the trusted host CLI. Stores only the one-time code hash."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    code=secrets.token_urlsafe(24)
    path=directory/'console-access.json'
    tmp=directory/('console-access-'+secrets.token_hex(8)+'.tmp')
    with tmp.open('x') as f:
        os.fchmod(f.fileno(),0o600)
        json.dump({'digest':hashlib.sha256(code.encode()).hexdigest(),'expires':time.time()+600},f)
    tmp.replace(path)
    return code


class ConsoleSessions:
    def __init__(self,directory):
        self.path=Path(directory)/'console-access.json'
        self.sessions={};self.lock=threading.Lock();self.failures=[]

    def login(self,code):
        with self.lock:
            now=time.time();self.failures=[t for t in self.failures if now-t<60]
            if len(self.failures)>=10:raise PermissionError('Too many attempts. Wait one minute.')
            try:record=json.loads(self.path.read_text())
            except (OSError,ValueError):record={}
            valid=(isinstance(code,str) and len(code)<=128 and record.get('expires',0)>now
                   and hmac.compare_digest(record.get('digest',''),hashlib.sha256(code.encode()).hexdigest()))
            if not valid:
                self.failures.append(now);raise PermissionError('Link expired or already used. Generate a new sign-in link.')
            self.path.unlink() # single use; possession of a host-generated code is required
            self.sessions={k:v for k,v in self.sessions.items() if v['expires']>now}
            if len(self.sessions)>=20:raise PermissionError('Too many active sessions.')
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
            self.sessions[token]={'csrf':csrf,'expires':now+3600}
            return token,csrf

    def token(self,headers):
        try:
            cookies=SimpleCookie();cookies.load(headers.get('Cookie',''))
            return cookies['scopedact_console'].value
        except (KeyError,ValueError):return None

    def verify(self,headers):
        with self.lock:
            session=self.sessions.get(self.token(headers))
            if (not session or session['expires']<=time.time() or
                not hmac.compare_digest(headers.get('X-ScopedAct-CSRF',''),session['csrf'])):
                raise PermissionError('Session expired. Generate a new sign-in link.')
            return OPERATOR

    def restore(self,headers):
        with self.lock:
            session=self.sessions.get(self.token(headers))
            if not session or session['expires']<=time.time():raise PermissionError('Sign in to the local lab.')
            return session['csrf']

    def logout(self,headers):
        self.verify(headers)
        with self.lock:self.sessions.pop(self.token(headers),None)
