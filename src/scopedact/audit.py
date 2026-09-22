from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    event_type: str
    task_id: str
    initiator: str
    actor: str
    parent_actor: str | None
    tool: str
    action: str
    resource: str
    decision: str
    reason_code: str
    request_id: str
    details: dict[str, Any]


class AuditLogger:
    REQUIRED_FIELDS = frozenset(AuditEvent.__dataclass_fields__)

    def __init__(self, output: str | Path | None = None, *, truncate: bool = True) -> None:
        self.output = Path(output) if output else None
        self.events: list[AuditEvent] = []
        if self.output:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            if truncate or not self.output.exists():
                self.output.write_text("", encoding="utf-8")

    def record(self, **values: Any) -> AuditEvent:
        details = values.pop("details", {})
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
            **values,
        )
        self.events.append(event)
        if self.output:
            with self.output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event

    @classmethod
    def has_required_fields(cls, event: AuditEvent) -> bool:
        return set(asdict(event)) == cls.REQUIRED_FIELDS
