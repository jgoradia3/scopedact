from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import re


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GrantStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True, order=True)
class Permission:
    action: str
    resource: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action, "resource": self.resource}


@dataclass
class TaskGrant:
    task_id: str
    initiator: str
    principal: str
    permissions: frozenset[Permission]
    expires_at: datetime
    status: GrantStatus = GrantStatus.ACTIVE
    parent_task_id: str | None = None
    delegation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if not self.task_id or not self.initiator or not self.principal:
            raise ValueError("task_id, initiator, and principal are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "initiator": self.initiator,
            "principal": self.principal,
            "permissions": [p.to_dict() for p in sorted(self.permissions)],
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "parent_task_id": self.parent_task_id,
            "delegation_id": self.delegation_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    task_id: str
    actor: str
    tool: str
    action: str
    resource: str
    parent_actor: str | None = None

    _IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")

    def __post_init__(self) -> None:
        for name in ("request_id", "task_id", "actor", "tool"):
            value = getattr(self, name)
            if not isinstance(value, str) or not self._IDENTIFIER.fullmatch(value):
                raise ValueError(f"{name} must be a namespaced identifier")
        # Resource syntax is distinct from principal identifiers. Filesystem
        # containment and canonical path validation belong to the connector.
        if (not isinstance(self.resource, str) or len(self.resource) > 2048
                or not re.fullmatch(r"[a-z][a-z0-9_-]*:[A-Za-z0-9._/-]+", self.resource)):
            raise ValueError("resource must be a namespaced resource")
        if not isinstance(self.action, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", self.action):
            raise ValueError("action must use lowercase letters, digits, and underscores")
        if self.parent_actor is not None and not self._IDENTIFIER.fullmatch(self.parent_actor):
            raise ValueError("parent_actor must be a namespaced identifier")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ActionRequest":
        expected = {"request_id", "task_id", "actor", "tool", "action", "resource", "parent_actor"}
        unknown = set(value) - expected
        missing = expected - set(value) - {"parent_actor"}
        if unknown:
            raise ValueError(f"unexpected request fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing request fields: {', '.join(sorted(missing))}")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "task_id": self.task_id,
            "actor": self.actor,
            "parent_actor": self.parent_actor,
            "tool": self.tool,
            "action": self.action,
            "resource": self.resource,
        }


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason_code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "message": self.message,
        }


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Approval:
    request_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None
