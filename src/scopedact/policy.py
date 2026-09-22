from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ActionPolicy:
    approval_required: bool = False


class PolicySet:
    def __init__(self, actions: dict[str, ActionPolicy] | None = None) -> None:
        self.actions = actions or {}

    @classmethod
    def from_json(cls, path: str | Path) -> "PolicySet":
        body = json.loads(Path(path).read_text(encoding="utf-8"))
        if set(body) != {"actions"} or not isinstance(body["actions"], dict):
            raise ValueError("policy must contain exactly one 'actions' object")
        actions: dict[str, ActionPolicy] = {}
        for name, settings in body["actions"].items():
            if set(settings) != {"approval_required"} or not isinstance(settings["approval_required"], bool):
                raise ValueError(f"invalid policy for action: {name}")
            actions[name] = ActionPolicy(settings["approval_required"])
        return cls(actions)

    def requires_approval(self, action: str) -> bool:
        return self.actions.get(action, ActionPolicy()).approval_required
