# Review ScopedAct without Docker

Download and extract the source ZIP, or clone the repository. Everything runs on
**your computer**. No cloud account, tunnel, or API key is needed.

## Install once

Install **Python 3.10 or newer** and [Ollama](https://ollama.com/download).
Open Ollama (on Linux, run `ollama serve` in another terminal).
Download the local model:

```sh
ollama pull qwen3:1.7b
```

From the extracted ScopedAct folder, install the Python package in a virtual environment:

macOS / Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python tools/start_native_review.py
```

Native setup currently targets macOS and Linux. On Windows, use the existing
Docker setup; native Windows support has not been implemented or validated.

There are no third-party Python runtime dependencies. Installation may download
build tooling. Ollama and its model are separate prerequisites; setup never silently
substitutes a scripted model. Model download and first inference can take several
minutes, depending on your connection and hardware.

## Start a review

The launcher checks Ollama, starts six local services, and opens the console at
`http://127.0.0.1:8891` with a private single-use sign-in link. Keep the terminal open.
The link is valid for ten minutes; the signed-in session lasts one hour.

1. Choose an evaluation role and read the incident brief.
2. Start an investigation. No investigation runs before you click.
3. Watch the current activity and resource map. The model chooses tool requests;
   ScopedAct checks each request before protected execution.
4. If access is denied, inspect the resource and decision. Continue with unchanged
   permissions, or end the evaluation. Continuing does not grant more access.
5. If the model proposes a repair, inspect the exact change before approving it.
   Apply the approved proposal and verify recovery using the console controls.
6. End the evaluation to revoke its remaining access.

The incident and roles are synthetic. The HTTP services, model calls, permission
checks, approval decisions and evidence are real. **A repair is not guaranteed.**
The model may stop, misunderstand evidence, or return an invalid tool call. An
unfinished investigation is not a successful recovery. There is no scripted fallback.
The existing ticket-pilot evaluation is a separate, explicitly scripted control test.

## Stop, restart, or sign in again

Ctrl+C stops the native lab; it does not stop your separately running Ollama app.
The private `.scopedact-native/` directory retains keys, journals and evidence.
Restart with the same start command. Interrupted work is not automatically replayed.

To generate a new link while the lab is running:

```sh
.venv/bin/python tools/start_native_review.py --link-only
```

If your Docker lab already occupies port 8891, use `--port 8892` on both the start
and link-only commands. To start with fresh evidence, use a new private directory:

```sh
.venv/bin/python tools/start_native_review.py --directory .scopedact-native/fresh-review --port 8892
```

If Ollama reports GPU initialization or allocation errors, restart the launcher with
`--cpu` to disable GPU offload. CPU inference may be slower.

An evidence directory cannot be used by two native launchers simultaneously.
Keep evidence directories outside commits and shared ZIPs. Use `--no-open` to print
the link without launching a browser. The installed `scopedact-review` command is
also available and accepts the same options.

## What this setup does and does not isolate

All services bind to loopback; internal ports are assigned automatically. Each API
still authenticates requests and the gateway enforces task permissions. The model
receives tool descriptions and resource results, not backend signing keys.

However, services run under your operating-system account. **Native mode does not
provide Docker's network segmentation, filesystem separation, or protection from
another process running as the same user.** This is a functional local review, not a
hostile-code sandbox. Use synthetic data. Use the [Docker lab](LIVE_INCIDENT_LAB.md)
for the documented container/network boundary evaluation. Neither deployment claims
production readiness or enterprise identity integration.

See [validation status](STABILIZATION_REVIEW.md) and [review questions](REVIEW_GUIDE.md).

For Ollama 0.35.0 in a restricted macOS execution environment, `--cpu` alone may
still trigger Metal initialization. The native validation used a separately started
Ollama server with `LLAMA_ARG_DEVICE=none OLLAMA_NO_CLOUD=1 ollama serve` and the
launcher `--cpu` option. This environment setting applies to that Ollama version's
llama.cpp backend. Ordinary desktop users need not set it unless GPU initialization
fails; do not start a second server on an occupied Ollama port.
