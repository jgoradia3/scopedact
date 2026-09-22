from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Permission


@dataclass(frozen=True)
class LifecycleConfig:
    initiator: str
    actor: str
    tool: str
    grant_lifetime_minutes: int
    upstream_authority: frozenset[Permission]
    task_permissions: frozenset[Permission]
    approval_required_actions: frozenset[str]

    @classmethod
    def load(cls, path: str | Path) -> "LifecycleConfig":
        body = json.loads(Path(path).read_text(encoding="utf-8"))
        expected = {
            "initiator", "actor", "tool", "grant_lifetime_minutes",
            "upstream_authority", "task_permissions", "approval_required_actions",
        }
        if set(body) != expected:
            raise ValueError(f"config keys must be exactly: {', '.join(sorted(expected))}")
        for name in ("initiator", "actor", "tool"):
            if not isinstance(body[name], str) or ":" not in body[name]:
                raise ValueError(f"{name} must be a namespaced identifier")
        lifetime = body["grant_lifetime_minutes"]
        if not isinstance(lifetime, int) or not 1 <= lifetime <= 1440:
            raise ValueError("grant_lifetime_minutes must be an integer from 1 to 1440")

        def permissions(name: str) -> frozenset[Permission]:
            values = body[name]
            if not isinstance(values, list):
                raise ValueError(f"{name} must be a list")
            try:
                result = frozenset(Permission(item["action"], item["resource"]) for item in values)
            except (KeyError, TypeError) as error:
                raise ValueError(f"{name} entries require action and resource") from error
            if any(set(item) != {"action", "resource"} for item in values):
                raise ValueError(f"{name} entries accept only action and resource")
            return result

        upstream = permissions("upstream_authority")
        task = permissions("task_permissions")
        if not task <= upstream:
            raise ValueError("task_permissions must be a subset of upstream_authority")
        approvals = body["approval_required_actions"]
        if not isinstance(approvals, list) or not all(isinstance(item, str) and item for item in approvals):
            raise ValueError("approval_required_actions must be a list of non-empty strings")
        return cls(
            body["initiator"], body["actor"], body["tool"], lifetime,
            upstream, task, frozenset(approvals),
        )


def default_config_path() -> Path:
    return Path("config/lifecycle.json")
