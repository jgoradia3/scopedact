from __future__ import annotations

import hashlib
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AGENT = 'agent:ticket-pilot'
CHILD = 'agent:diagnostic'
OPERATOR = 'human:pilot-operator'
TOOL = 'tool:tickets'
MAX_BODY = 16384


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def secret_file(path):
    value = Path(path).read_text(encoding='utf-8').strip()
    if len(value) < 32:
        raise ValueError('secret file must contain at least 32 characters')
    return value


def env_secret(name):
    path = os.environ.get(name)
    if not path:
        raise ValueError(f'{name} must name a secret file')
    return secret_file(path)


def ticket_id(resource):
    if not isinstance(resource, str) or not re.fullmatch(r'ticket:T-[0-9]{1,8}', resource):
        raise ValueError('resource must use ticket:T-<digits>')
    return resource.split(':', 1)[1]


def request_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'request:[A-Za-z0-9_-]{1,80}', value):
        raise ValueError('invalid request ID')
    return value


def validate_input(value):
    if not isinstance(value, dict) or set(value) != {'text', 'expected_version'}:
        raise ValueError('update input requires text and expected_version')
    if not isinstance(value['text'], str) or not value['text'].strip() or len(value['text']) > 4000:
        raise ValueError('text must contain 1 to 4000 characters')
    if type(value['expected_version']) is not int or value['expected_version'] < 1:
        raise ValueError('expected_version must be a positive integer')


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


class Handler(BaseHTTPRequestHandler):
    def body(self):
        if self.headers.get('Transfer-Encoding') or self.headers.get_content_type() != 'application/json':
            raise ValueError('bounded JSON body required')
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1:
            raise ValueError('one Content-Length required')
        size = int(lengths[0])
        if not 2 <= size <= MAX_BODY:
            raise ValueError('body too large or empty')
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise ValueError('incomplete body')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError('JSON object required')
        return raw, value

    def reply(self, status, value):
        raw = canonical(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass
