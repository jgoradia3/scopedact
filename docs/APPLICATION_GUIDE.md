# Protected workspace application

The workspace application is ScopedAct's primary v0.11 experience. It provides a real local tool with controlled side effects, not a precomputed pass/fail simulation.

## Workflow

1. `scopedact init` creates an isolated `.scopedact/workspace` and editable exact-authority policy.
2. `scopedact doctor` validates the project before services start.
3. `scopedact serve` starts the operator console, authority gateway, and protected workspace tool on loopback.
4. `scopedact create-task` issues a short-lived task from the reviewed policy.
5. `scopedact invoke` submits signed list, read, append, or delete proposals.
6. The operator can approve sensitive operations and pause, resume, revoke, or close the task.

## Workspace safety rules

- Paths must be relative and resolve beneath the generated workspace.
- Absolute paths, traversal with `..`, and symbolic links are rejected.
- Directory listings omit dot-prefixed entries.
- Reads are limited to UTF-8 text files of at most 64 KiB.
- Append requires an existing file and 1–4000 input characters.
- Delete can operate only on a file inside the workspace and is not granted by default.
- The tool endpoint rejects calls without the runtime gateway credential.

These controls reduce mistakes in a local evaluation. They are not operating-system sandboxing. A process running under the same user account remains inside the same host trust boundary.

## Change the authority

Edit `.scopedact/lifecycle.json`. `task_permissions` must remain a subset of `upstream_authority`. Every permission is an exact action/resource pair; there are no implicit wildcards.

After editing, run:

```bash
scopedact doctor
```

Create a new task after policy changes. Existing grants do not expand automatically.

## Approval resumption

An approval binds the request ID to its task, actor, tool, action, resource, and input hash. After approval, the client resubmits the same proposal with a fresh signed transport nonce. Any attempt to alter the reviewed content is rejected.
