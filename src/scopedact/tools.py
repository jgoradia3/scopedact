from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtectedTool(Protocol):
    """Minimal interface for a service protected by ScopedAct."""

    tool_name: str

    def execute(self, action: str, resource: str) -> Any:
        """Execute an already-authorized action against a resource."""
        ...


class ToolRegistry:
    """Routes an authorized request to a named protected tool."""

    def __init__(self) -> None:
        self._tools: dict[str, ProtectedTool] = {}

    def register(self, name: str, tool: ProtectedTool) -> None:
        if name in self._tools:
            raise ValueError(f"duplicate tool: {name}")
        self._tools[name] = tool

    def execute(self, tool: str, action: str, resource: str) -> Any:
        try:
            protected = self._tools[tool]
        except KeyError as error:
            raise ValueError(f"unknown tool: {tool}") from error
        return protected.execute(action, resource)


class RoutedTool:
    """ProtectedTool adapter around a ToolRegistry."""

    def __init__(self, registry: ToolRegistry, tool_name: str) -> None:
        self.registry = registry
        self.tool_name = tool_name

    def execute(self, action: str, resource: str) -> Any:
        return self.registry.execute(self.tool_name, action, resource)
