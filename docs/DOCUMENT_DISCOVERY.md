# Document discovery and operator clarification

The reviewer-facing workflow is the [staging authentication incident evaluation](INCIDENT_EVALUATION.md).
It uses a current and an archived authentication runbook to test whether a document-name
search pauses for an explicit applicability decision.

Discovery searches only names within the task's current read permissions. It does not
read document bodies or reveal unpermitted candidate names. Multiple matches stop the
runner before any matching document is read. The operator chooses a result in the
console; the runner rechecks access when resumed. A selection cannot override pause,
expiry, revocation, or document permissions.

`scopedact-agent find --task TASK_ID --name authentication-runbook` provides a repeatable
lookup without a model; supply the agent key and journal using the global options.
The Ollama agent also has a `find_document` tool, but a natural-language prompt does not
guarantee it will choose that tool. Resuming an ambiguous lookup reads the chosen document
and stops; it does not continue the prior model conversation.

Searches and selected candidates are attached to the caller's branch in the task map.
They are metadata events, counted separately from document reads and writes. Exports
include search strings and candidate names, so review exports before sharing them.

The current store uses unique flat identifiers and UTF-8 text documents. Extensions are
labels, not PDF/Word parser support. Real folders, cross-folder duplicates, AWS/S3 search,
and external folder/object ACLs require additional connectors and are not implemented.
