"""Synthetic REST ticket service: transactional updates and idempotency receipts."""
from __future__ import annotations

import hmac
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from .common import Handler, Server, canonical, digest, request_id, validate_input


class Conflict(ValueError):
    pass


class TicketStore:
    def __init__(self, database):
        self.database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
            ''')
            for identifier, title in [('T-100', 'Sandbox login issue'), ('T-200', 'Unassigned billing question')]:
                body = {'id': identifier, 'title': title, 'version': 1, 'comments': []}
                db.execute('INSERT OR IGNORE INTO tickets VALUES (?,?)', (identifier, canonical(body)))

    def connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def read(self, identifier):
        db = self.connect()
        try:
            row = db.execute('SELECT body FROM tickets WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise KeyError(identifier)
            return json.loads(row[0])
        finally:
            db.close()

    def receipt(self, identifier):
        db = self.connect()
        try:
            row = db.execute('SELECT fingerprint,result FROM operations WHERE id=?', (identifier,)).fetchone()
            return {'found': False} if row is None else {
                'found': True, 'fingerprint': row[0], 'result': json.loads(row[1])}
        finally:
            db.close()

    def update(self, identifier, operation_id, value):
        request_id(operation_id)
        validate_input(value)
        fingerprint = digest({'resource': f'ticket:{identifier}', 'input': value})
        db = self.connect()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT fingerprint,result FROM operations WHERE id=?', (operation_id,)).fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise Conflict('idempotency key is bound to another operation')
                    return json.loads(row[1])
                row = db.execute('SELECT body FROM tickets WHERE id=?', (identifier,)).fetchone()
                if row is None:
                    raise KeyError(identifier)
                ticket = json.loads(row[0])
                if ticket['version'] != value['expected_version']:
                    raise Conflict('ticket version changed; read and obtain fresh approval')
                if len(ticket['comments']) >= 100:
                    raise Conflict('synthetic ticket comment limit reached')
                ticket['comments'].append(value['text'])
                ticket['version'] += 1
                result = {'id': identifier, 'version': ticket['version'], 'comment_added': True}
                db.execute('UPDATE tickets SET body=? WHERE id=?', (canonical(ticket), identifier))
                db.execute('INSERT INTO operations VALUES (?,?,?)', (operation_id, fingerprint, canonical(result)))
                return result
        finally:
            db.close()


def build_backend(host, port, *, database, key):
    store = TicketStore(database)

    class TicketHandler(Handler):
        def authorized(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + key):
                self.reply(401, {'error': 'tool credential required'})
                return False
            return True

        def do_GET(self):
            if self.path == '/health':
                self.reply(200, {'status': 'healthy', 'service': 'synthetic-tickets'})
                return
            if not self.authorized():
                return
            try:
                if re.fullmatch(r'/tickets/T-[0-9]{1,8}', self.path):
                    self.reply(200, store.read(self.path.rsplit('/', 1)[1]))
                elif re.fullmatch(r'/operations/request:[A-Za-z0-9_-]{1,80}', self.path):
                    self.reply(200, store.receipt(self.path.rsplit('/', 1)[1]))
                else:
                    self.reply(404, {'error': 'not found'})
            except KeyError:
                self.reply(404, {'error': 'ticket not found'})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                if not re.fullmatch(r'/tickets/T-[0-9]{1,8}/comments', self.path):
                    self.reply(404, {'error': 'not found'})
                    return
                _, body = self.body()
                result = store.update(self.path.split('/')[2], self.headers.get('Idempotency-Key'), body)
                self.reply(200, result)
            except Conflict as error:
                self.reply(409, {'error': str(error)})
            except (ValueError, TypeError, KeyError):
                self.reply(400, {'error': 'invalid ticket update'})
            except sqlite3.Error:
                self.reply(503, {'error': 'storage unavailable'})

    return Server((host, port), TicketHandler)
