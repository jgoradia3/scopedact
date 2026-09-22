from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

class Connector(Protocol):
    connector_name: str
    tool_name: str
    supported_actions: frozenset[str]
    def health(self) -> dict[str,Any]: ...
    def execute(self,action:str,resource:str) -> Any: ...

@dataclass(frozen=True)
class ConnectorDescriptor:
    name: str; tool: str; actions: tuple[str,...]

class ConnectorRegistry:
    def __init__(self): self._items: dict[str,Connector]={}
    def register(self,connector:Connector):
        if connector.connector_name in self._items: raise ValueError(f"duplicate connector: {connector.connector_name}")
        if not connector.tool_name.startswith("tool:") or not connector.supported_actions: raise ValueError("invalid connector contract")
        self._items[connector.connector_name]=connector
    def get(self,name:str)->Connector:
        if name not in self._items: raise ValueError(f"unknown connector: {name}")
        return self._items[name]
    def describe(self): return tuple(ConnectorDescriptor(n,c.tool_name,tuple(sorted(c.supported_actions))) for n,c in sorted(self._items.items()))
    def check_health(self,name:str): return self.get(name).health()


@dataclass(frozen=True)
class ExecutionContext:
    """Canonical per-call context; keep request ID stable across retries."""
    request_id: str
    task_id: str
    actor: str
    input: Any = None


class ContextConnector(Protocol):
    """Opt-in extension; the legacy two-argument Connector remains supported."""
    connector_name: str
    tool_name: str
    supported_actions: frozenset[str]
    def health(self) -> dict[str, Any]: ...
    def execute_context(self, action: str, resource: str, context: ExecutionContext) -> Any: ...
    def reconcile(self, context: ExecutionContext) -> dict[str, Any]: ...
