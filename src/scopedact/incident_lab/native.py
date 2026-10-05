"""Loopback-only native review lab. Same controls, no container isolation."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import webbrowser

from .__main__ import OperationsAdapter
from .services import PortalStore, identity_service, portal_service, operations_service
from .reviewer import Worker, Guide, worker_service, scenario_service
from ..workspace.agent import OllamaModel
from ..workspace.server import build_workspace
from ..workspace.sessions import ConsoleSessions, issue_access


def initialize(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = root / 'secrets'
    directory.mkdir(exist_ok=True, mode=0o700)
    keys = {}
    for name in ('identity', 'signing', 'portal', 'fault', 'operations', 'agent', 'child', 'operator', 'reviewer-control'):
        path = directory / (name + '.key')
        try:
            with path.open('x') as output:
                os.chmod(path, 0o600)
                output.write(secrets.token_urlsafe(48) + '\n')
        except FileExistsError:
            pass
        keys[name] = path.read_text().strip()
        if len(keys[name]) < 32:
            raise ValueError('Invalid local key file: ' + str(path))
    return keys


class NativeLab:
    """Trusted local launcher; all services run as the same operating-system user."""
    def __init__(self, root, port=8891, model_factory=None):
        self.root = Path(root)
        self.servers = []
        self.threads = []
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = sqlite3.connect(self.root / "launcher.lock.db", timeout=0)
        try:
            self.lock.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as exc:
            self.lock.close()
            raise ValueError("This evidence directory is already in use by another native lab.") from exc
        try:
            self.keys = initialize(self.root)
        except BaseException:
            self.lock.close()
            raise
        k = self.keys
        def start(server):
            self.servers.append(server)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)
            return 'http://127.0.0.1:' + str(server.server_port)
        try:
            identity = start(identity_service('127.0.0.1', 0, k['identity'], k['signing']))
            portal = start(portal_service('127.0.0.1', 0, k['portal'], k['signing'],
                PortalStore(self.root / 'portal.db'), identity, k['identity'], fault_key=k['fault']))
            operations = start(operations_service('127.0.0.1', 0, k['operations'], portal, k['portal']))
            scenario = start(scenario_service('127.0.0.1', 0, k['reviewer-control'], portal, k['portal'], k['fault']))
            # Bind the console before creating a worker so port conflicts fail without a run.
            guide = Guide(self.root, '', scenario, k['reviewer-control'])
            gateway = build_workspace('127.0.0.1', port, database=self.root / 'gateway.db',
                documents=OperationsAdapter(operations, k['operations']), agent_key=k['agent'],
                child_key=k['child'], operator_key=k['operator'], console_sessions=ConsoleSessions(self.root), guide=guide)
            self.url = start(gateway)
            self.worker = Worker(self.root / 'reviewer-journal', self.url, k['agent'], model_factory=model_factory)
            guide.worker_url = start(worker_service('127.0.0.1', 0, k['reviewer-control'], self.worker))
        except BaseException:
            self.close()
            raise

    def link(self):
        return self.url + '/#access=' + issue_access(self.root)

    def close(self):
        for server in reversed(self.servers):
            server.shutdown()
            server.server_close()
        self.servers.clear()
        for thread in self.threads:
            thread.join(timeout=2)
        self.threads.clear()
        self.lock.close()


def check_model(name, endpoint):
    model = OllamaModel(name, endpoint)  # Enforces loopback, no proxies or redirects.
    try:
        with model.opener.open(model.base + '/api/tags', timeout=5) as response:
            data = json.loads(response.read(1048576))
    except Exception as exc:
        raise ValueError('Start the Ollama app (or run ollama serve), then try again.') from exc
    if name not in {item.get('name') for item in data.get('models', [])}:
        raise ValueError('Local model is missing. Run: ollama pull ' + name)
    return model


def main():
    parser = argparse.ArgumentParser(description='Run the real-agent ScopedAct console without Docker')
    parser.add_argument('--directory', default='.scopedact-native', help='private local evidence directory')
    parser.add_argument('--port', type=int, default=8891)
    parser.add_argument('--model', default='qwen3:1.7b')
    parser.add_argument('--ollama', default='http://127.0.0.1:11434')
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--cpu', action='store_true', help='disable GPU offload if the local GPU cannot load the model')
    parser.add_argument('--link-only', action='store_true', help='print a fresh sign-in link for an already running lab')
    args = parser.parse_args()
    if os.name == "nt":
        parser.exit(1, "Native mode currently supports macOS/Linux. Use the Docker launcher on Windows.\n")
    root = Path(args.directory).resolve()
    if args.link_only:
        if not (root / 'gateway.db').exists():
            parser.error('Start this native lab before requesting a new link.')
        print(f'http://127.0.0.1:{args.port}/#access=' + issue_access(root))
        return
    try:
        check_model(args.model, args.ollama)
        lab = NativeLab(root, args.port, model_factory=lambda: OllamaModel(args.model, args.ollama, cpu=args.cpu))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\nIf the console port is occupied, stop the other lab or use --port 8892.\n')
    try:
        link = lab.link()
        print('Real-agent local review ready. Synthetic incident; live model decisions.\n'
              'Native mode has no container/network isolation. Use only synthetic data.\n'
              'Keep this terminal open; Ctrl+C stops the lab. Evidence is saved in ' + str(root) + '\n'
              'Private sign-in link (single use, valid 10 minutes; session lasts 1 hour):\n' + link, flush=True)
        if not args.no_open:
            webbrowser.open(link)
        threading.Event().wait()
    except KeyboardInterrupt:
        print('\nStopping local services. Saved evidence is retained.')
    finally:
        lab.close()


if __name__ == '__main__':
    main()
