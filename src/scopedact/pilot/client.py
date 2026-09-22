from __future__ import annotations
import json
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit
from ..lab import sign_headers
from .connector import NoRedirect
from .common import canonical


class Client:
    def __init__(self, base, actor, key):
        parsed = urlsplit(base)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}):
            raise ValueError('gateway URL must be an origin')
        if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', 'gateway'}:
            raise ValueError('remote gateway requires HTTPS')
        self.base, self.actor, self.key = base.rstrip('/'), actor, key
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def post(self, path, value, **signing):
        raw = canonical(value).encode()
        headers = sign_headers('POST', path, raw, self.actor, self.key, **signing)
        req = Request(self.base + path, data=raw, headers=headers, method='POST')
        try:
            response = self.opener.open(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(2097153)
            if len(raw) > 2097152:
                raise ValueError('gateway response exceeds client limit')
            return response.code, json.loads(raw)
