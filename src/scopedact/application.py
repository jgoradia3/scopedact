"""GitHub-ready local application: project setup and a protected workspace tool."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import closing
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .grants import SQLiteGrantRegistry
from .lab import ApiAuthenticator, _json_response, request_gateway
from .lifecycle import LifecycleGateway, LifecycleStore, run_id
from .lifecycle_config import LifecycleConfig
from .models import ActionRequest
from .mvp import initialize_demo_task
from .policy import ActionPolicy, PolicySet


PROJECT_FILE = "project.json"
KEY_FILE = "client.key"


@dataclass(frozen=True)
class ApplicationProject:
    directory: Path
    name: str
    actor: str
    initiator: str
    tool: str
    workspace: Path
    database: Path
    lifecycle_config: Path
    client_key: Path
    gateway_port: int
    tool_port: int
    dashboard_port: int

    @classmethod
    def load(cls, directory: str | Path = ".scopedact") -> "ApplicationProject":
        base = Path(directory).resolve()
        path = base / PROJECT_FILE
        if not path.is_file():
            raise ValueError(f"ScopedAct project not found: {path}. Run 'scopedact init'.")
        body = json.loads(path.read_text(encoding="utf-8"))
        expected = {"name", "actor", "initiator", "tool", "workspace", "database", "lifecycle_config", "client_key", "ports"}
        if set(body) != expected or set(body.get("ports", {})) != {"gateway", "tool", "dashboard"}:
            raise ValueError("project.json has an unsupported shape")
        def within(value: str) -> Path:
            result = (base / value).resolve()
            if result != base and base not in result.parents:
                raise ValueError("project paths must remain inside .scopedact")
            return result
        ports = body["ports"]
        if any(not isinstance(ports[name], int) or not 1024 <= ports[name] <= 65535 for name in ports):
            raise ValueError("project ports must be integers from 1024 to 65535")
        return cls(base, body["name"], body["actor"], body["initiator"], body["tool"], within(body["workspace"]), within(body["database"]), within(body["lifecycle_config"]), within(body["client_key"]), ports["gateway"], ports["tool"], ports["dashboard"])


def initialize_application(directory: str | Path = ".scopedact") -> ApplicationProject:
    base = Path(directory).resolve()
    if base.exists() and any(base.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty project directory: {base}")
    base.mkdir(parents=True, exist_ok=True)
    workspace = base / "workspace"
    workspace.mkdir()
    (workspace / "welcome.md").write_text(
        "# ScopedAct workspace\n\nThis file is readable by the example agent.\n",
        encoding="utf-8",
    )
    (workspace / "notes.md").write_text("# Reviewed notes\n", encoding="utf-8")
    actor = "agent:workspace"
    initiator = "human:operator"
    tool = "tool:workspace"
    permissions = [
        {"action": "list", "resource": "folder:."},
        {"action": "read", "resource": "file:welcome.md"},
        {"action": "read", "resource": "file:notes.md"},
        {"action": "append", "resource": "file:notes.md"},
    ]
    lifecycle = {
        "initiator": initiator,
        "actor": actor,
        "tool": tool,
        "grant_lifetime_minutes": 60,
        "upstream_authority": permissions,
        "task_permissions": permissions,
        "approval_required_actions": ["append", "delete"],
    }
    (base / "lifecycle.json").write_text(json.dumps(lifecycle, indent=2) + "\n", encoding="utf-8")
    project = {
        "name": "workspace-guard",
        "actor": actor,
        "initiator": initiator,
        "tool": tool,
        "workspace": "workspace",
        "database": "scopedact.db",
        "lifecycle_config": "lifecycle.json",
        "client_key": KEY_FILE,
        "ports": {"dashboard": 8765, "gateway": 8770, "tool": 8780},
    }
    (base / PROJECT_FILE).write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    key_path = base / KEY_FILE
    key_path.write_text(secrets.token_urlsafe(40) + "\n", encoding="utf-8")
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return ApplicationProject.load(base)


def diagnose_application(directory: str | Path = ".scopedact") -> dict[str, Any]:
    project = ApplicationProject.load(directory)
    checks: list[dict[str, Any]] = []
    for name, path, expected in (
        ("workspace", project.workspace, "directory"),
        ("lifecycle_config", project.lifecycle_config, "file"),
        ("client_key", project.client_key, "file"),
    ):
        healthy = path.is_dir() if expected == "directory" else path.is_file()
        checks.append({"name": name, "healthy": healthy, "path": str(path)})
    try:
        config = LifecycleConfig.load(project.lifecycle_config)
        config_ok = config.actor == project.actor and config.tool == project.tool
    except (ValueError, OSError, json.JSONDecodeError):
        config_ok = False
    checks.append({"name": "policy", "healthy": config_ok, "path": str(project.lifecycle_config)})
    key_ok = project.client_key.is_file() and len(project.client_key.read_text(encoding="utf-8").strip()) >= 32
    checks.append({"name": "client_key_strength", "healthy": key_ok, "path": str(project.client_key)})
    return {"healthy": all(item["healthy"] for item in checks), "project": project.name, "checks": checks}


class WorkspaceTool:
    tool_name = "tool:workspace"

    def __init__(self, root: str | Path, input_value: Any = None) -> None:
        self.root = Path(root).resolve()
        self.input_value = input_value

    def _resolve(self, resource: str, prefix: str) -> Path:
        if not resource.startswith(prefix):
            raise ValueError(f"resource must start with {prefix}")
        relative = resource.removeprefix(prefix)
        if not relative or relative.startswith(('/', '\\')):
            raise ValueError("resource path must be relative")
        parts = Path(relative).parts
        if ".." in parts:
            raise ValueError("parent traversal is not supported")
        candidate = self.root
        for part in parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("symbolic links are not supported")
        result = candidate.resolve()
        if result != self.root and self.root not in result.parents:
            raise ValueError("resource escapes the configured workspace")
        if result.is_symlink():
            raise ValueError("symbolic links are not supported")
        return result

    def execute(self, action: str, resource: str) -> Any:
        if action == "list":
            folder = self._resolve(resource, "folder:")
            if not folder.is_dir():
                raise ValueError("folder does not exist")
            return {"entries": [str(path.relative_to(self.root)) for path in sorted(folder.iterdir()) if not path.name.startswith(".")]}
        path = self._resolve(resource, "file:")
        if action == "read":
            if not path.is_file():
                raise ValueError("file does not exist")
            if path.stat().st_size > 65536:
                raise ValueError("file exceeds the 64 KiB preview limit")
            return {"path": str(path.relative_to(self.root)), "content": path.read_text(encoding="utf-8")}
        if action == "append":
            if not path.is_file():
                raise ValueError("append target must already exist")
            if not isinstance(self.input_value, str) or not self.input_value.strip() or len(self.input_value) > 4000:
                raise ValueError("append input must contain 1 to 4000 characters")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(self.input_value.rstrip() + "\n")
            return {"path": str(path.relative_to(self.root)), "appended": True}
        if action == "delete":
            if not path.is_file():
                raise ValueError("file does not exist")
            path.unlink()
            return {"path": str(path.relative_to(self.root)), "deleted": True}
        raise ValueError(f"unsupported workspace action: {action}")


class HttpWorkspaceTool:
    def __init__(self, url: str, internal_key: str, tool_name: str, input_value: Any = None) -> None:
        self.url, self.internal_key, self.tool_name, self.input_value = url, internal_key, tool_name, input_value

    def execute(self, action: str, resource: str) -> Any:
        body = json.dumps({"action": action, "resource": resource, "input": self.input_value}, sort_keys=True).encode()
        request = urllib.request.Request(self.url + "/execute", data=body, headers={"Content-Type": "application/json", "X-ScopedAct-Internal-Key": self.internal_key}, method="POST")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())['value']


def build_workspace_tool_server(host: str, port: int, internal_key: str, root: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            _json_response(self, 200, {"status": "healthy", "service": "workspace-tool"}) if self.path == "/health" else self.send_error(404)
        def do_POST(self):
            if self.path != "/execute": self.send_error(404); return
            if not hmac.compare_digest(self.headers.get("X-ScopedAct-Internal-Key", ""), internal_key): _json_response(self, 401, {"error": "gateway authentication required"}); return
            try:
                size = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(size))
                value = WorkspaceTool(root, payload.get("input")).execute(payload["action"], payload["resource"])
                _json_response(self, 200, {"value": value})
            except (ValueError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as error:
                _json_response(self, 400, {"error": str(error)})
        def log_message(self, format, *args): return
    return ThreadingHTTPServer((host, port), Handler)


def _bind_request_input(database: str, request_id: str, input_value: Any) -> None:
    digest = hashlib.sha256(json.dumps(input_value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE IF NOT EXISTS application_inputs(request_id TEXT PRIMARY KEY, input_hash TEXT NOT NULL)")
        row = connection.execute("SELECT input_hash FROM application_inputs WHERE request_id = ?", (request_id,)).fetchone()
        if row and row[0] != digest:
            raise ValueError("pending request input cannot be changed")
        connection.execute("INSERT OR IGNORE INTO application_inputs VALUES (?, ?)", (request_id, digest))


def build_application_gateway(host: str, port: int, *, project: ApplicationProject, tool_url: str, internal_key: str):
    config = LifecycleConfig.load(project.lifecycle_config)
    key = project.client_key.read_text(encoding="utf-8").strip()
    auth = ApiAuthenticator(project.database, {config.actor: key})
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            _json_response(self, 200, {"status": "healthy", "service": "scopedact-gateway"}) if self.path == "/health" else self.send_error(404)
        def do_POST(self):
            path = urlparse(self.path).path
            if path not in {"/v1/tasks", "/v1/actions"}: self.send_error(404); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if self.headers.get_content_type() != "application/json" or not 2 <= size <= 12288: raise ValueError("valid JSON body required")
                body = self.rfile.read(size); client = auth.verify("POST", path, body, self.headers); payload = json.loads(body)
                if client != config.actor: raise PermissionError("client is not the configured actor")
                if path == "/v1/tasks":
                    if payload != {"template": "default"}: raise ValueError("default reviewed template required")
                    task_id = initialize_demo_task(project.database, project.lifecycle_config)
                    _json_response(self, 201, {"task_id": task_id, "status": "active"}); return
                required = {"task_id", "request_id", "action", "resource"}
                if set(payload) not in (required, required | {"input"}): raise ValueError("action request has invalid fields")
                if payload["action"] == "append":
                    value = payload.get("input")
                    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
                        raise ValueError("append requires 1 to 4000 input characters")
                elif "input" in payload:
                    raise ValueError("input is supported only for the append action")
                # Legacy input binding retained for compatibility; full canonical binding
                # and atomic execution claims are enforced in LifecycleGateway.
                _bind_request_input(str(project.database), payload["request_id"], payload.get("input"))
                store = LifecycleStore(project.database); registry = SQLiteGrantRegistry(project.database)
                try:
                    task = store.get_task(payload["task_id"])
                    if task is None: raise ValueError("unknown task")
                    request = ActionRequest(request_id=payload["request_id"], task_id=payload["task_id"], actor=client, parent_actor=task.initiator, tool=config.tool, action=payload["action"], resource=payload["resource"])
                    policy = PolicySet({name: ActionPolicy(True) for name in config.approval_required_actions})
                    gateway = LifecycleGateway(AuthorizationEvaluator(registry), HttpWorkspaceTool(tool_url, internal_key, config.tool, payload.get("input")), store, AuditLogger(project.database.with_suffix(".jsonl"), truncate=False), policy)
                    result = gateway.invoke(request, input_value=payload.get("input"))
                    _json_response(self, 200, {"request_id": payload["request_id"], "decision": result.decision.reason_code, "executed": result.decision.allowed, "value": result.value})
                finally: store.close(); registry.close()
            except PermissionError as error: _json_response(self, 401, {"error": str(error)})
            except urllib.error.HTTPError as error: _json_response(self, 502, {"error": "protected tool rejected the authorized operation", "tool_status": error.code})
            except (ValueError, KeyError, OSError, json.JSONDecodeError) as error: _json_response(self, 400, {"error": str(error)})
        def log_message(self, format, *args): return
    return ThreadingHTTPServer((host, port), Handler)


def serve_application(directory: str | Path = ".scopedact") -> None:
    project = ApplicationProject.load(directory)
    if not diagnose_application(directory)["healthy"]: raise ValueError("project diagnostics failed; run 'scopedact doctor'")
    host = "127.0.0.1"; internal = secrets.token_urlsafe(32)
    tool = build_workspace_tool_server(host, project.tool_port, internal, project.workspace)
    gateway = build_application_gateway(host, project.gateway_port, project=project, tool_url=f"http://{host}:{project.tool_port}", internal_key=internal)
    for server in (tool, gateway): threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Project:           {project.name}")
    print(f"Operator console:  http://{host}:{project.dashboard_port}")
    print(f"ScopedAct gateway: http://{host}:{project.gateway_port}")
    print(f"Protected tool:    http://{host}:{project.tool_port} (gateway-only)")
    print("NEXT: open another terminal and run 'scopedact create-task'")
    from .dashboard import serve_dashboard
    try: serve_dashboard(project.database, host, project.dashboard_port, project.lifecycle_config)
    finally:
        gateway.shutdown(); tool.shutdown(); gateway.server_close(); tool.server_close()


def create_application_task(directory: str | Path = ".scopedact") -> dict[str, Any]:
    project = ApplicationProject.load(directory); key = project.client_key.read_text(encoding="utf-8").strip()
    status, result = request_gateway(f"http://127.0.0.1:{project.gateway_port}", "/v1/tasks", {"template": "default"}, project.actor, key)
    if status != 201: raise RuntimeError(result)
    return result


def invoke_application(*, directory: str | Path = ".scopedact", task_id: str, action: str, resource: str, input_value: str | None = None, request_id: str | None = None) -> dict[str, Any]:
    project = ApplicationProject.load(directory); key = project.client_key.read_text(encoding="utf-8").strip()
    payload: dict[str, Any] = {"task_id": task_id, "request_id": request_id or run_id("request-app"), "action": action, "resource": resource}
    if input_value is not None: payload["input"] = input_value
    status, result = request_gateway(f"http://127.0.0.1:{project.gateway_port}", "/v1/actions", payload, project.actor, key)
    return {"http_status": status, **result}
