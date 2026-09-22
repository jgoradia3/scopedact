from __future__ import annotations

import json
import hashlib
import sqlite3
from dataclasses import asdict, dataclass
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .gateway import GatewayResult
from .grants import GrantRegistry
from .models import ActionRequest, ApprovalStatus, Decision, Permission, TaskGrant, utc_now
from .policy import PolicySet
from .tools import ProtectedTool


class TaskStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    REVOKED = "revoked"
    CLOSED = "closed"


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    initiator: str
    actor: str
    status: TaskStatus
    created_at: str
    updated_at: str


class LifecycleStore:
    """Durable local state for the authority-lifecycle demonstration."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        self.connection = sqlite3.connect(self.database)
        try:
            self.connection.row_factory = sqlite3.Row
            with self.connection:
                self.connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS execution_claims (
                        request_id TEXT PRIMARY KEY, canonical TEXT NOT NULL,
                        state TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS upstream_authority (
                        principal TEXT NOT NULL, action TEXT NOT NULL, resource TEXT NOT NULL,
                        PRIMARY KEY(principal, action, resource)
                    );
                    CREATE TABLE IF NOT EXISTS lifecycle_tasks (
                        task_id TEXT PRIMARY KEY, initiator TEXT NOT NULL, actor TEXT NOT NULL,
                        status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lifecycle_requests (
                        request_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, actor TEXT NOT NULL,
                        tool TEXT NOT NULL, action TEXT NOT NULL, resource TEXT NOT NULL,
                        decision TEXT NOT NULL, reason_code TEXT NOT NULL, executed INTEGER NOT NULL,
                        outcome TEXT, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lifecycle_attempts (
                        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL, task_id TEXT NOT NULL,
                        action TEXT NOT NULL, resource TEXT NOT NULL,
                        decision TEXT NOT NULL, reason_code TEXT NOT NULL,
                        executed INTEGER NOT NULL, timestamp TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lifecycle_approvals (
                        request_id TEXT PRIMARY KEY, status TEXT NOT NULL,
                        reviewer TEXT, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lifecycle_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL, task_id TEXT NOT NULL, request_id TEXT,
                        details TEXT NOT NULL, previous_hash TEXT NOT NULL DEFAULT '',
                        event_hash TEXT NOT NULL DEFAULT ''
                    );
                    CREATE TABLE IF NOT EXISTS connector_status (
                        name TEXT PRIMARY KEY, status TEXT NOT NULL,
                        details TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    """
                )
                columns = {row[1] for row in self.connection.execute("PRAGMA table_info(lifecycle_events)")}
                if "previous_hash" not in columns:
                    self.connection.execute("ALTER TABLE lifecycle_events ADD COLUMN previous_hash TEXT NOT NULL DEFAULT ''")
                if "event_hash" not in columns:
                    self.connection.execute("ALTER TABLE lifecycle_events ADD COLUMN event_hash TEXT NOT NULL DEFAULT ''")
            self._backfill_event_hashes()
        except BaseException:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def add_authority(self, principal: str, permissions: set[Permission] | frozenset[Permission]) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT OR IGNORE INTO upstream_authority(principal, action, resource) VALUES (?, ?, ?)",
                [(principal, item.action, item.resource) for item in permissions],
            )

    def authority_for(self, principal: str) -> frozenset[Permission]:
        rows = self.connection.execute(
            "SELECT action, resource FROM upstream_authority WHERE principal = ?", (principal,)
        ).fetchall()
        return frozenset(Permission(row["action"], row["resource"]) for row in rows)

    def create_task(self, task_id: str, initiator: str, actor: str) -> TaskRecord:
        now = utc_now().isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO lifecycle_tasks VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, initiator, actor, TaskStatus.ACTIVE.value, now, now),
            )
        self.event("task_created", task_id, None, {"initiator": initiator, "actor": actor})
        return TaskRecord(task_id, initiator, actor, TaskStatus.ACTIVE, now, now)

    def get_task(self, task_id: str) -> TaskRecord | None:
        row = self.connection.execute(
            "SELECT * FROM lifecycle_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        return TaskRecord(
            row["task_id"], row["initiator"], row["actor"], TaskStatus(row["status"]),
            row["created_at"], row["updated_at"],
        )

    def set_task_status(self, task_id: str, status: TaskStatus) -> None:
        now = utc_now().isoformat()
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE lifecycle_tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                (status.value, now, task_id),
            )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown task: {task_id}")
        self.event("task_status_changed", task_id, None, {"status": status.value})

    def get_request(self, request_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM lifecycle_requests WHERE request_id = ?", (request_id,)
        ).fetchone()

    def record_request(self, request: ActionRequest, decision: Decision, value: Any = None) -> None:
        now = utc_now().isoformat()
        outcome = json.dumps(value, sort_keys=True, default=str) if value is not None else None
        values = (
            request.request_id, request.task_id, request.actor, request.tool, request.action,
            request.resource, "allow" if decision.allowed else "deny", decision.reason_code,
            int(decision.allowed), outcome, now,
        )
        with self.connection:
            self.connection.execute(
                """INSERT INTO lifecycle_attempts(
                   request_id, task_id, action, resource, decision, reason_code,
                   executed, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (request.request_id, request.task_id, request.action, request.resource,
                 values[6], decision.reason_code, int(decision.allowed), now),
            )
            if decision.reason_code not in {"REPLAY_DETECTED", "REQUEST_MISMATCH", "REQUEST_IN_PROGRESS", "REQUEST_REISSUE_REQUIRED"}:
                self.connection.execute(
                    """INSERT INTO lifecycle_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(request_id) DO UPDATE SET
                       decision=excluded.decision, reason_code=excluded.reason_code,
                       executed=excluded.executed, outcome=excluded.outcome,
                       updated_at=excluded.updated_at""",
                    values,
                )
        self.event("authorization_decision", request.task_id, request.request_id, {
            "decision": values[6], "reason_code": decision.reason_code,
            "action": request.action, "resource": request.resource,
        })

    def request_approval(self, request_id: str, task_id: str) -> None:
        now = utc_now().isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO lifecycle_approvals VALUES (?, ?, NULL, ?)",
                (request_id, ApprovalStatus.PENDING.value, now),
            )
        self.event("approval_requested", task_id, request_id, {})

    def decide_approval(self, request_id: str, reviewer: str, approved: bool) -> None:
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        now = utc_now().isoformat()
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE lifecycle_approvals SET status = ?, reviewer = ?, updated_at = ? WHERE request_id = ? AND status = 'pending'",
                (status.value, reviewer, now, request_id),
            )
        if cursor.rowcount != 1:
            raise ValueError(f"no pending approval: {request_id}")
        row = self.get_request(request_id)
        self.event("approval_decided", row["task_id"] if row else "task:unknown", request_id, {
            "status": status.value, "reviewer": reviewer,
        })

    def approval_status(self, request_id: str) -> ApprovalStatus | None:
        row = self.connection.execute(
            "SELECT status FROM lifecycle_approvals WHERE request_id = ?", (request_id,)
        ).fetchone()
        return ApprovalStatus(row["status"]) if row else None

    def event(self, event_type: str, task_id: str, request_id: str | None, details: dict[str, Any]) -> None:
        timestamp = utc_now().isoformat()
        detail_text = json.dumps(details, sort_keys=True, separators=(",", ":"))
        # Serialize head selection and insert across SQLite connections.
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            previous = self.connection.execute(
                "SELECT event_hash FROM lifecycle_events ORDER BY event_id DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous["event_hash"] if previous else ""
            event_hash = self._event_hash(timestamp, event_type, task_id, request_id, detail_text, previous_hash)
            self.connection.execute(
                "INSERT INTO lifecycle_events(timestamp, event_type, task_id, request_id, details, previous_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (timestamp, event_type, task_id, request_id, detail_text, previous_hash, event_hash),
            )

    def claim_request(self, request: ActionRequest, input_value: Any = None) -> str | None:
        canonical = json.dumps({**request.to_dict(), "input": input_value},
                               sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute(
                "SELECT * FROM execution_claims WHERE request_id=?", (request.request_id,)
            ).fetchone()
            if row:
                if row["canonical"] != canonical:
                    return "REQUEST_MISMATCH"
                if row["state"] == "evaluating":
                    return "REQUEST_IN_PROGRESS"
                if row["state"] != "pending":
                    return "REPLAY_DETECTED"
            elif self.get_request(request.request_id):
                # Legacy records have no verifiable input binding: never resume them.
                return "REQUEST_REISSUE_REQUIRED"
            self.connection.execute(
                "INSERT INTO execution_claims VALUES (?, ?, 'evaluating', ?) "
                "ON CONFLICT(request_id) DO UPDATE SET state='evaluating', updated_at=excluded.updated_at",
                (request.request_id, canonical, utc_now().isoformat()),
            )
        return None

    def finish_claim(self, request_id: str, state: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE execution_claims SET state=?, updated_at=? WHERE request_id=?",
                (state, utc_now().isoformat(), request_id),
            )

    @staticmethod
    def _event_hash(timestamp: str, event_type: str, task_id: str, request_id: str | None, details: str, previous_hash: str) -> str:
        payload = json.dumps({
            "timestamp": timestamp, "event_type": event_type, "task_id": task_id,
            "request_id": request_id, "details": details, "previous_hash": previous_hash,
        }, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()

    def _backfill_event_hashes(self) -> None:
        rows = self.connection.execute("SELECT * FROM lifecycle_events ORDER BY event_id").fetchall()
        if not rows or any(row["event_hash"] for row in rows):
            return
        previous = ""
        with self.connection:
            for row in rows:
                digest = self._event_hash(row["timestamp"], row["event_type"], row["task_id"], row["request_id"], row["details"], previous)
                if row["previous_hash"] != previous or row["event_hash"] != digest:
                    self.connection.execute(
                        "UPDATE lifecycle_events SET previous_hash = ?, event_hash = ? WHERE event_id = ?",
                        (previous, digest, row["event_id"]),
                    )
                previous = digest

    def verify_event_chain(self) -> dict[str, Any]:
        previous = ""
        count = 0
        for row in self.connection.execute("SELECT * FROM lifecycle_events ORDER BY event_id"):
            count += 1
            digest = self._event_hash(row["timestamp"], row["event_type"], row["task_id"], row["request_id"], row["details"], previous)
            if row["previous_hash"] != previous or row["event_hash"] != digest:
                return {"valid": False, "events": count, "failing_event_id": row["event_id"]}
            previous = digest
        return {"valid": True, "events": count, "failing_event_id": None, "head": previous}

    def record_connector_status(self, name: str, status: str, details: dict[str, Any]) -> None:
        now = utc_now().isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO connector_status VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET status=excluded.status, details=excluded.details, updated_at=excluded.updated_at",
                (name, status, json.dumps(details, sort_keys=True), now),
            )

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for key, table, order in (
            ("tasks", "lifecycle_tasks", "created_at DESC"),
            ("requests", "lifecycle_requests", "updated_at DESC"),
            ("attempts", "lifecycle_attempts", "attempt_id DESC"),
            ("approvals", "lifecycle_approvals", "updated_at DESC"),
            ("events", "lifecycle_events", "event_id DESC"),
            ("connectors", "connector_status", "updated_at DESC"),
        ):
            rows = self.connection.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
            result[key] = [dict(row) for row in rows]
        authority_rows = self.connection.execute(
            "SELECT principal, action, resource FROM upstream_authority ORDER BY principal, action, resource"
        ).fetchall()
        result["upstream_authority"] = [dict(row) for row in authority_rows]
        has_grants = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'grants'"
        ).fetchone()
        grants: list[dict[str, Any]] = []
        if has_grants:
            for row in self.connection.execute("SELECT body, revoked FROM grants ORDER BY task_id").fetchall():
                body = json.loads(row["body"])
                grants.append({
                    "task_id": body["task_id"], "principal": body["principal"],
                    "permissions": ", ".join(
                        f"{item['action']} -> {item['resource']}" for item in body["permissions"]
                    ),
                    "expires_at": body["expires_at"], "revoked": bool(row["revoked"]),
                })
        result["grants"] = grants
        for approval in result["approvals"]:
            claim = self.connection.execute(
                "SELECT canonical, state FROM execution_claims WHERE request_id=?",
                (approval["request_id"],),
            ).fetchone()
            approval["request"] = json.loads(claim["canonical"]) if claim else None
            approval["execution_state"] = claim["state"] if claim else "legacy"
        result["executions"] = [dict(row) for row in self.connection.execute(
            "SELECT request_id, state, updated_at FROM execution_claims ORDER BY updated_at DESC"
        )]
        return result


class AuthorityError(ValueError):
    pass


class GrantIssuer:
    """Issues a task grant only from locally recorded upstream authority."""

    def __init__(self, store: LifecycleStore, registry: GrantRegistry) -> None:
        self.store = store
        self.registry = registry

    def issue(
        self,
        *,
        task_id: str,
        initiator: str,
        actor: str,
        permissions: set[Permission],
        lifetime: timedelta = timedelta(minutes=15),
    ) -> TaskGrant:
        upstream = self.store.authority_for(initiator)
        excess = permissions - upstream
        if excess:
            rendered = ", ".join(f"{p.action}:{p.resource}" for p in sorted(excess))
            raise AuthorityError(f"requested authority exceeds initiator authority: {rendered}")
        grant = TaskGrant(
            task_id=task_id, initiator=initiator, principal=actor,
            permissions=frozenset(permissions), expires_at=utc_now() + lifetime,
            metadata={"authority_source": "local-upstream-provider"},
        )
        self.registry.register(grant)
        self.store.create_task(task_id, initiator, actor)
        self.store.event("grant_issued", task_id, None, {
            "permissions": [item.to_dict() for item in sorted(permissions)]
        })
        return grant


class LifecycleOperator:
    def __init__(self, store: LifecycleStore, registry: GrantRegistry) -> None:
        self.store = store
        self.registry = registry

    def pause(self, task_id: str) -> None:
        task = self._require(task_id, TaskStatus.ACTIVE)
        self.store.set_task_status(task.task_id, TaskStatus.PAUSED)

    def resume(self, task_id: str) -> None:
        task = self._require(task_id, TaskStatus.PAUSED)
        self.store.set_task_status(task.task_id, TaskStatus.ACTIVE)

    def revoke(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None or task.status in {TaskStatus.REVOKED, TaskStatus.CLOSED}:
            raise ValueError("task cannot be revoked from its current state")
        self.registry.revoke(task_id)
        self.store.set_task_status(task_id, TaskStatus.REVOKED)

    def close_task(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None or task.status in {TaskStatus.REVOKED, TaskStatus.CLOSED}:
            raise ValueError("task cannot be closed from its current state")
        self.registry.revoke(task_id)
        self.store.set_task_status(task_id, TaskStatus.CLOSED)

    def approve(self, request_id: str, reviewer: str) -> None:
        self.store.decide_approval(request_id, reviewer, True)

    def reject(self, request_id: str, reviewer: str) -> None:
        self.store.decide_approval(request_id, reviewer, False)

    def _require(self, task_id: str, expected: TaskStatus) -> TaskRecord:
        task = self.store.get_task(task_id)
        if task is None or task.status is not expected:
            raise ValueError(f"task must be {expected.value}")
        return task


class LifecycleGateway:
    """Durable gateway used by the authority-lifecycle MVP."""

    def __init__(
        self,
        evaluator: AuthorizationEvaluator,
        service: ProtectedTool,
        store: LifecycleStore,
        audit: AuditLogger,
        policy: PolicySet | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.service = service
        self.store = store
        self.audit = audit
        self.policy = policy or PolicySet()

    def invoke(self, request: ActionRequest, *, input_value: Any = None) -> GatewayResult:
        conflict = self.store.claim_request(request, input_value)
        if conflict:
            decision = Decision(False, conflict, "Request binding or execution claim rejected.")
            self.store.record_request(request, decision)
            return GatewayResult(decision, None)
        try:
            return self._invoke_claimed(request)
        except Exception:
            # No automatic retry after an ambiguous failure. The tool may have acted.
            self.store.finish_claim(request.request_id, "unknown")
            raise

    def _invoke_claimed(self, request: ActionRequest) -> GatewayResult:
        existing = self.store.get_request(request.request_id)
        approval = self.store.approval_status(request.request_id)
        resumable = bool(existing and existing["reason_code"] == "APPROVAL_REQUIRED" and approval is not None)
        if existing and not resumable:
            decision = Decision(False, "REPLAY_DETECTED", "Request identifier has already reached a terminal result.")
        else:
            task = self.store.get_task(request.task_id)
            if task is None:
                decision = Decision(False, "TASK_NOT_FOUND", "No lifecycle task exists.")
            elif task.status is not TaskStatus.ACTIVE:
                decision = Decision(False, "TASK_NOT_ACTIVE", f"Task is {task.status.value}.")
            elif request.tool != self.service.tool_name:
                decision = Decision(False, "TOOL_MISMATCH", "Request names a different protected tool.")
            else:
                decision = self.evaluator.evaluate(request)
                if decision.allowed and self.policy.requires_approval(request.action):
                    if approval is None or approval is ApprovalStatus.PENDING:
                        self.store.request_approval(request.request_id, request.task_id)
                        decision = Decision(False, "APPROVAL_REQUIRED", "A human approval is required.")
                    elif approval is ApprovalStatus.REJECTED:
                        decision = Decision(False, "APPROVAL_REJECTED", "The human approval was rejected.")
        if decision.allowed:
            self.store.event("execution_dispatch", request.task_id, request.request_id,
                             {"action": request.action, "resource": request.resource})
        value = self.service.execute(request.action, request.resource) if decision.allowed else None
        self.store.record_request(request, decision, value)
        grant = self.evaluator.registry.get(request.task_id)
        self.audit.record(
            event_type="authorization_decision", task_id=request.task_id,
            initiator=grant.initiator if grant else "unknown", actor=request.actor,
            parent_actor=request.parent_actor, tool=request.tool, action=request.action,
            resource=request.resource, decision="allow" if decision.allowed else "deny",
            reason_code=decision.reason_code, request_id=request.request_id,
            details={"executed": decision.allowed, "durable": True},
        )
        self.store.finish_claim(request.request_id,
                                "pending" if decision.reason_code == "APPROVAL_REQUIRED"
                                else "succeeded" if decision.allowed else "denied")
        return GatewayResult(decision, value)


def run_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:12]}"
