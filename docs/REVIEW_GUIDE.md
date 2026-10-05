# Security reviewer guide

For the latest live-service workflow, start with the [incident lab](LIVE_INCIDENT_LAB.md).
Keep model success, enforcement correctness and independent review findings separate.

Start with the [staging authentication incident evaluation](INCIDENT_EVALUATION.md).
It provides a concrete investigation, a permission matrix, deliberate negative tests,
expected outcomes, and a results worksheet. The primary questions are whether the agent
stays within its assigned resources, whether approval and later intervention compose
correctly, and whether the map supports reconstruction of what happened.

The scripted harness is repeatable test equipment, not evidence of autonomous reasoning
or external adoption. A separate optional local-model path is documented in that guide.
Use synthetic resources first and report actual observations in your own words.

## Earlier support-ticket evaluation

Evaluate the documented synthetic pilot, not a production system. No cloud credentials or paid model are needed.

## Reproduce

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests -v
python -W error::ResourceWarning tools/check_sqlite_resources.py
scopedact-pilot init
docker compose -f compose.pilot.yaml up --build -d --wait
scopedact-pilot evaluate --output pilot-results/ticket.json
scopedact-pilot evaluate-delegation --output pilot-results/delegation.json
python pilot/verify_isolation.py
scopedact-pilot export --output pilot-results/evidence.json
```

Skip init if configured already; use `init-child` when upgrading from v0.13. Use a new review directory if unsure.

## Review one claim at a time

1. Use the [manual ticket workflow](TICKET_PILOT.md) to approve an exact update. Try substituting its task, resource, or content.
2. Use the [delegation walkthrough](DELEGATION.md) to grant a child read-only access. Try privilege/resource/lifetime expansion and parent-grant reuse.
3. Pause or revoke the parent, then try the next child action. Do not interpret this as cancellation of an already-dispatched operation.
4. Inspect `scopedact-pilot lineage --task-id PARENT_ID`. Confirm initiator, parent, child, action, tool, decision, and outcome match the actual calls.
5. Test uncertain-execution reconciliation or read its regression tests. Check that unknown effects are not retried automatically.
6. Confirm the declared role-key and network boundaries. A trusted evaluation harness holds multiple keys; the included isolated probes do not.

## Return actionable feedback

Record release checksum, OS/Python/Docker versions, commands, expected and observed behavior, and a minimal synthetic reproducer. State exactly what you reviewed, whether you ran it, and any relationship to the author. A review is not an endorsement or a production deployment.

Use the security-reporting policy for sensitive issues; do not attach credentials, database contents, or company data to public issues. The exported examples contain only synthetic data and redact proposal bodies/read results, but real metadata could still be sensitive.

After evaluation, `docker compose -f compose.pilot.yaml down` stops services and keeps volumes. See the capability matrix and release-validation record for what was and was not tested.
