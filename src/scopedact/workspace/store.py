"""Versioned text documents, not an arbitrary host-filesystem adapter.

Document replacement, history and receipt commit in one SQLite transaction.
Identifiers never become filesystem paths. Only the trusted operator imports files.
"""
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from ..pilot.common import canonical, digest, request_id
from ..pilot.connector import ConnectorError


def document_id(resource):
    if not isinstance(resource, str) or not re.fullmatch(r'doc:[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', resource):
        raise ValueError('expected doc:<simple-name>; paths are not accepted')
    return resource


def validate_replacement(value):
    if (not isinstance(value, dict) or set(value) != {'text', 'expected_version'}
            or not isinstance(value['text'], str) or len(value['text'].encode()) > 8000
            or type(value['expected_version']) is not int or value['expected_version'] < 1):
        raise ValueError('replacement requires text (up to 8000 bytes) and a positive expected_version')


class DocumentStore:
    def __init__(self, database):
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS documents(resource TEXT PRIMARY KEY, version INTEGER, text TEXT);
                CREATE TABLE IF NOT EXISTS document_versions(resource TEXT, version INTEGER, text TEXT,
                    PRIMARY KEY(resource,version));
                CREATE TABLE IF NOT EXISTS document_receipts(request_id TEXT PRIMARY KEY, fingerprint TEXT, result TEXT);
            ''')

    def connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def import_text(self, resource, text):
        document_id(resource)
        validate_replacement({'text': text, 'expected_version': 1})
        with closing(self.connect()) as db, db:
            db.execute('INSERT INTO documents VALUES (?,1,?)', (resource, text))
            db.execute('INSERT INTO document_versions VALUES (?,1,?)', (resource, text))

    def catalog(self):
        with closing(self.connect()) as db:
            return [{'resource': r, 'version': v} for r,v in db.execute('SELECT resource,version FROM documents ORDER BY resource')]

    def read(self, resource):
        document_id(resource)
        with closing(self.connect()) as db:
            row = db.execute('SELECT version,text FROM documents WHERE resource=?', (resource,)).fetchone()
        if row is None:
            raise ConnectorError('document_not_found', definite=True)
        return {'resource': resource, 'version': row[0], 'text': row[1]}

    def receipt(self, identifier):
        request_id(identifier)
        with closing(self.connect()) as db:
            row = db.execute('SELECT fingerprint,result FROM document_receipts WHERE request_id=?', (identifier,)).fetchone()
        return {'found': False} if row is None else {'found': True, 'fingerprint': row[0], 'result': json.loads(row[1])}

    def update(self, resource, identifier, value):
        document_id(resource); request_id(identifier); validate_replacement(value)
        fingerprint = digest({'resource': resource, 'input': value})
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT fingerprint,result FROM document_receipts WHERE request_id=?', (identifier,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise ConnectorError('operation_binding_conflict', definite=True)
                return json.loads(previous[1])
            row = db.execute('SELECT version FROM documents WHERE resource=?', (resource,)).fetchone()
            if row is None or row[0] != value['expected_version']:
                raise ConnectorError('document_version_conflict', definite=True)
            version = row[0] + 1
            result = {'resource': resource, 'version': version, 'content_sha256': digest(value['text'])}
            db.execute('UPDATE documents SET version=?,text=? WHERE resource=?', (version,value['text'],resource))
            db.execute('INSERT INTO document_versions VALUES (?,?,?)', (resource,version,value['text']))
            db.execute('INSERT INTO document_receipts VALUES (?,?,?)', (identifier,fingerprint,canonical(result)))
            return result


class DocumentConnector:
    tool_name = 'tool:managed-workspace'
    supported_actions = frozenset({'read', 'update'})

    def __init__(self, store):
        self.store = store
        self.tool_name = getattr(store, "tool_name", self.tool_name)

    def bind(self, context):
        connector = self
        class Bound:
            tool_name = connector.tool_name
            def execute(self, action, resource):
                if action == 'read':
                    return connector.store.read(resource)
                if action == 'update':
                    return connector.store.update(resource, context.request_id, context.input)
                raise ValueError('unsupported document action')
        return Bound()

    def reconcile(self, context):
        return self.store.receipt(context.request_id)
