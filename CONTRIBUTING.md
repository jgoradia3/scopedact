# Contributing

Use synthetic data and describe the security property your change affects. Do not
include employer/customer material, credentials, private evaluation journals or
unpublished research artifacts. Keep cloud accounts and paid services optional.

## Set up and check a change

From the repository root, with Python 3.10+ and Node.js 22 available:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python tools/check_repository.py
.venv/bin/python -W error::ResourceWarning tools/check_sqlite_resources.py
node tests/test_console_actions.cjs
.venv/bin/python examples/quickstart.py
.venv/bin/python -m pip install build
.venv/bin/python -m build
```

The SQLite checker runs the complete Python test suite and fails on unclosed
connections. `make test PYTHON=.venv/bin/python` runs repository, Python and console
checks together. Builds require the optional `build` development tool.

For runtime or deployment changes, follow the affected [Docker evaluation](docs/DOCKER.md)
and inspect hosted CI. Model-based changes also need a separately reported live-model
run; model doubles are useful regressions, not evidence of model reliability.

## Find the relevant code

- `src/scopedact/incident_lab/`: native launcher, live services, assignment policy and guided worker.
- `src/scopedact/workspace/`: authenticated console, map, sessions and constrained model runner; also supports the managed-document example.
- `src/scopedact/pilot/`: signed API, fixed-route connector, backend and delegation evaluation.
- Shared modules in `src/scopedact/`: grants, lifecycle, approvals, evidence and process-local SDK.
- `tests/`: security, integration and console regressions. Older versioned test names still exercise supported behavior.
- `tools/` and `pilot/`: launchers, validation and container helpers.
- `docs/`: [documentation index](docs/START_HERE.md), including explicitly separated historical evidence.

Keep authorization enforced outside the model. Explain behavior, validation and
remaining limitations in your pull request. Report sensitive vulnerabilities through
[SECURITY.md](SECURITY.md), not public issues.
