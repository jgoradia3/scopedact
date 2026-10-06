> Separate reference example. For the current live-service incident console, start with [native review](NATIVE_REVIEW.md). Do not mix the setup commands across these workflows.

# A real local agent, with ScopedAct controlling its tools

The model chooses document reads and proposes replacement text. Every supported tool
call goes through the existing signed gateway and appears in the task activity map.
The runner has three tools: `find_document`, `read_document`, and `propose_update`.
[Name lookup and user selection](DOCUMENT_DISCOVERY.md) handle ambiguous matches. It cannot create tasks,
approve requests, run shell commands, or access arbitrary URLs through these tools.

## Start the workspace and model

Install the source, then initialize once and start the gateway:

```sh
python -m pip install .
scopedact-workspace init
scopedact-workspace serve
```

Install [Ollama](https://ollama.com/download) and run it locally. In another terminal:

```sh
ollama pull qwen3:1.7b
```

The adapter uses Ollama's [native chat and tool-calling API](https://docs.ollama.com/api/chat).
Models must support tools. Model output quality varies; a model that answers without
calling tools has not demonstrated tool execution. Downloads require Internet access;
the runner sends prompts and retrieved documents only to the selected loopback server.

### Docker alternative for Ollama

If Docker is already available, the local evaluation can also use:

```sh
docker run -d --name scopedact-ollama-evaluation \
  -p 127.0.0.1:11434:11434 -v scopedact-ollama-models:/root/.ollama \
  -e OLLAMA_NO_CLOUD=1 -e OLLAMA_NUM_PARALLEL=1 \
  ollama/ollama@sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01
# Wait until this responds before pulling the model:
curl http://127.0.0.1:11434/api/version
docker exec scopedact-ollama-evaluation ollama pull qwen3:1.7b
```

This downloads a container image and model and consumes several GB of disk space.
CPU-only inference can be slow. Stop the evaluation server with
`docker stop scopedact-ollama-evaluation`; the model volume remains for reuse. Restart an existing evaluation container with
`docker start scopedact-ollama-evaluation` instead of running `docker run` again.

## Create authority as the operator

```sh
scopedact-workspace create-task \
  --summary 'Investigate repeated login failures and improve the runbook' \
  --read doc:runbook.md --read doc:diagnostics.md --update doc:runbook.md \
  --lifetime 3600
```

Copy the returned task ID. Start the **separate agent runner** with only its own key:

```sh
scopedact-agent --agent-key .scopedact-workspace/secrets/agent.key \
  --state /tmp/scopedact-agent-run.json run --task TASK_ID \
  --prompt 'Read doc:runbook.md and doc:diagnostics.md. Investigate repeated login failures. Call propose_update to submit a concise improvement to doc:runbook.md based on the diagnostic evidence, Preserve the existing guidance. Do not merely describe an update.'
```

Use a new state filename for each run. The prompt is an instruction to the model,
not a grant of permission. The operator's explicit task scope is authoritative.
The prompt is retained in the private local journal, not automatically included in
shared gateway evidence. The map title uses the operator's task summary.

## Review, then retry the same proposal

Open http://127.0.0.1:8890 and select the operator key file. Select the assignment.
The map shows actual requests from `agent:ticket-pilot` (the existing development
role). Review the current and proposed document text. Approve only the exact change
you want. Then run:

```sh
scopedact-agent --agent-key .scopedact-workspace/secrets/agent.key \
  --state /tmp/scopedact-agent-run.json resume
```

The runner binds replacements to the version returned by a successful read; the
model does not choose the version number. A proposal without a prior read is rejected.

Resume does not ask the model to regenerate text: it retries the saved request ID
and exact input. Approval does not override revocation, pause, expiry, or a changed
document version. A successful resume stops; it does not launch more model actions.
An approval in this walkthrough is a human decision. Automated test approvals must
be described as automated, not as evidence that a human reviewed the proposal.

## What to test independently

- Does the model choose useful reads and propose an evidence-based change?
- Does the map make those requests understandable?
- Does a request for `doc:unassigned.md` get denied and stop the run?
- If you pause or revoke after approval, does the retry remain blocked?
- Can you find the proposal and its execution result in exported gateway metadata?

Record model name, task ID, date, setup, actual result, and problems encountered.
Use synthetic or non-sensitive documents for an initial evaluation.

## Boundaries

This is a single primary-agent integration, not autonomous multi-agent orchestration.
The scripted helper demo still exists separately. No semantic intent-drift detector,
host-wide capture, or automatic discovery of an organization's APIs is included.
The model sees successful read results; prompts and pending replacement text are
sensitive local data. Run journals have mode 0600 and must not be committed/shared.
The runner defaults to eight model calls and twelve tool attempts, stopping at the
first denial, held proposal, or gateway error. Unknown tool names and malformed
arguments are rejected locally and do not appear as gateway events. A model call can
take up to 180 seconds. A gateway timeout preserves the request for operator
investigation; automatic uncertain retries are deliberately unavailable.

The runner never reads the document database or operator key. Running it as the
same host OS user is **not** a sandbox: that user still has OS access. Existing
container isolation probes concern the provided probe containers, not this native
runner. The local model endpoint is trusted configuration; a loopback URL alone does
not prove what that separately managed server does with data. No cloud credentials
are needed by this adapter.

Use one process per journal; do not edit a pending journal. Gateway exact-request
binding protects a stored proposal against changed retries, but the local journal
is not independently attested. Tool history, not the model's final prose, is the
source of truth about what executed. The runner labels final prose `model_answer_unverified`;
`model_finished` means the model stopped requesting tools, not that it accomplished
the assignment. `confirmed_updates` counts only executed update tool calls in that run.
