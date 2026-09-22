from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from pathlib import Path

from .models import GrantStatus, TaskGrant


class GrantError(ValueError):
    """Raised when a grant is structurally invalid."""


class GrantRegistry:
    """Small in-memory registry suitable only for deterministic demonstrations."""

    def __init__(self) -> None:
        self._grants: dict[str, TaskGrant] = {}
        self._revoked: set[str] = set()

    def register(self, grant: TaskGrant) -> None:
        if grant.task_id in self._grants:
            raise GrantError(f"duplicate task_id: {grant.task_id}")
        self._grants[grant.task_id] = grant

    def get(self, task_id: str) -> TaskGrant | None:
        return self._grants.get(task_id)

    def revoke(self, task_id: str) -> bool:
        if task_id not in self._grants:
            return False
        self._revoked.add(task_id)
        return True

    def is_revoked(self, task_id: str) -> bool:
        return task_id in self._revoked


class SQLiteGrantRegistry(GrantRegistry):
    """Durable local grant registry for demonstrations and integration tests."""

    def __init__(self, database: str | Path) -> None:
        super().__init__()
        self.database = str(database)
        self._connection = sqlite3.connect(self.database)
        try:
            with self._connect() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS grants (task_id TEXT PRIMARY KEY, body TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)"
                )
        except BaseException:
            self._connection.close()
            raise

    def close(self) -> None:
        """Release the owned SQLite connection; transaction contexts do not close it."""
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _connect(self) -> sqlite3.Connection:
        return self._connection

    def register(self, grant: TaskGrant) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO grants(task_id, body, revoked) VALUES (?, ?, 0)",
                    (grant.task_id, json.dumps(grant.to_dict(), sort_keys=True)),
                )
        except sqlite3.IntegrityError as error:
            raise GrantError(f"duplicate task_id: {grant.task_id}") from error

    def get(self, task_id: str) -> TaskGrant | None:
        with self._connect() as connection:
            row = connection.execute("SELECT body FROM grants WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        body = json.loads(row[0])
        from .models import Permission
        return TaskGrant(
            task_id=body["task_id"], initiator=body["initiator"], principal=body["principal"],
            permissions=frozenset(Permission(**item) for item in body["permissions"]),
            expires_at=datetime.fromisoformat(body["expires_at"]), status=GrantStatus(body["status"]),
            parent_task_id=body["parent_task_id"], delegation_id=body["delegation_id"], metadata=body["metadata"],
        )

    def revoke(self, task_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("UPDATE grants SET revoked = 1 WHERE task_id = ?", (task_id,))
        return cursor.rowcount == 1

    def is_revoked(self, task_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT revoked FROM grants WHERE task_id = ?", (task_id,)).fetchone()
        return bool(row and row[0])


def validate_child_grant(parent: TaskGrant, child: TaskGrant, now: datetime) -> None:
    """Apply a simple, static, single-parent subset check.

    This is intentionally a basic single-parent permission check.
    """
    if child.parent_task_id != parent.task_id:
        raise GrantError("child parent_task_id does not reference the parent")
    if child.initiator != parent.initiator:
        raise GrantError("child must preserve the initiating principal")
    if child.status is not GrantStatus.ACTIVE:
        raise GrantError("child grant must be active when issued")
    if parent.status is not GrantStatus.ACTIVE or parent.expires_at <= now:
        raise GrantError("parent grant is inactive")
    if child.expires_at > parent.expires_at:
        raise GrantError("child expiration exceeds parent expiration")
    extra = child.permissions - parent.permissions
    if extra:
        rendered = ", ".join(f"{p.action}:{p.resource}" for p in sorted(extra))
        raise GrantError(f"child authority exceeds parent: {rendered}")
