# Reading and reporting evidence

A model response, an authorization decision, a tool execution and verified recovery
are different events. Report them separately.

| Observation | What it establishes |
|---|---|
| Allowed request | The recorded request passed the applicable gateway checks |
| Denied request | That request was refused; inspect dispatch evidence or backend receipts when testing non-execution |
| Approved proposal | A reviewer approved exact content; later authority checks still apply |
| Applied change | The protected service reports a completed mutation |
| Recovery verified | A fresh verification succeeded for this synthetic incident |
| Agent finished | The runner stopped; this alone establishes neither repair nor recovery |

## Reproduce a finding

Record the commit, environment, setup path, model (if used), access profile, steps,
request IDs, expected result and observed result. Export evidence from the console
and inspect it before sharing. Never attach access links, keys, raw databases or
private model journals. Exports may retain sensitive resource names and metadata.
See the [review guide](REVIEW_GUIDE.md) for the reporting template.

Local event chains and separately persisted backend receipts support inspection.
They are not immutable third-party evidence: an administrator controlling the host
can modify state. See [limitations](LIMITATIONS.md).

## Keep results tied to their source

Use [the control-to-test map](CONTROL_TEST_MAP.md) for deterministic regressions and
[the validation record](STABILIZATION_REVIEW.md) for dated maintainer runs. Historical
counts describe those runs only. A successful scripted test does not establish
live-model reliability, independent adoption, or effectiveness against arbitrary attacks.
Keep failed runs and criticism. Attribute independent feedback only with permission.
