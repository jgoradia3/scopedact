"""REST connector with fixed routes, bounded I/O, and explicit execution context."""
from __future__ import annotations

import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError, URLError
from .common import TOOL, canonical, ticket_id, request_id, validate_input


from ..connectors import ExecutionContext, ContextConnector


class ConnectorError(RuntimeError):
    def __init__(self, category, *, definite=False):
        super().__init__(category)
        self.category = category
        self.definite = definite


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class TicketRestConnector:
    connector_name = 'ticket-rest'
    tool_name = TOOL
    supported_actions = frozenset({'read', 'update'})

    def __init__(self, base_url, key, *, timeout=3, allow_local_http=False):
        parsed = urlsplit(base_url)
        if (parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {'', '/'} or not parsed.hostname):
            raise ValueError('connector base URL must be an origin without credentials or path')
        if parsed.scheme != 'https':
            if not (allow_local_http and parsed.scheme == 'http'
                    and parsed.hostname in {'127.0.0.1', 'localhost', 'ticket-api'}):
                raise ValueError('HTTPS required except explicit local pilot transport')
        if not 0 < timeout <= 30:
            raise ValueError('timeout must be between zero and 30 seconds')
        self.base = base_url.rstrip('/')
        self.key, self.timeout = key, timeout
        # Never inherit host proxy credentials or follow redirects with tool secrets.
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _call(self, method, path, body=None, operation_id=None):
        headers = {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'}
        if operation_id:
            headers['Idempotency-Key'] = request_id(operation_id)
        request = Request(self.base + path, data=canonical(body).encode() if body is not None else None,
                          headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(1048577)
                if len(raw) > 1048576 or response.headers.get_content_type() != 'application/json':
                    raise ConnectorError('invalid_response')
                return json.loads(raw)
        except HTTPError as error:
            error.close()
            # Only this declared backend's 4xx contract guarantees no mutation.
            raise ConnectorError('conflict' if error.code == 409 else f'http_{error.code}',
                                 definite=error.code in {400, 401, 404, 409}) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ConnectorError('transport_or_response_unknown') from None

    def execute_context(self, action, resource, context):
        identifier = ticket_id(resource)
        request_id(context.request_id)
        if action == 'read':
            if context.input is not None:
                raise ValueError('read does not accept input')
            return self._call('GET', '/tickets/' + identifier)
        if action == 'update':
            validate_input(context.input)
            return self._call('POST', '/tickets/' + identifier + '/comments', context.input, context.request_id)
        raise ValueError('unsupported ticket action')

    def health(self):
        return self._call('GET', '/health')

    def reconcile(self, context):
        return self._call('GET', '/operations/' + request_id(context.request_id))

    def bind(self, context):
        connector = self
        class BoundTool:
            tool_name = TOOL
            def execute(self, action, resource):
                return connector.execute_context(action, resource, context)
        return BoundTool()
