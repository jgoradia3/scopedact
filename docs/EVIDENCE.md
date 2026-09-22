# Evidence and Measurement Guidance

## Reproducible evidence

Run:

```bash
python -m unittest discover -s tests -v
scopedact lifecycle-demo
```

Version 0.11.0 supports reporting:

- 68 included unit, integration, HTTP-boundary, and explanation tests passed in the release validation run;

- predefined tests passed or failed;
- predefined scenarios passed or failed;
- unauthorized action attempts blocked in those fixtures;
- benign authorized actions completed in those fixtures;
- invalid child expansions rejected in those fixtures;
- expired and revoked requests rejected;
- presence of required audit fields; and
- decision reason-code counts.
- grant issuance rejected when a requested permission is absent from the local
  upstream-authority record;
- approval, pause, resume, and close behavior in the included lifecycle fixture;
- durable request, attempt, approval, outcome, and event records across local
  process restarts; and
- dashboard HTML and JSON state rendering against the included local database.

## Claims discipline

Use a statement tied to a version, command, environment, and fixture set. Example:

> All included automated tests passed for ScopedAct version 0.11.0 on the documented local run. Live-model and real-cloud paths require separate environment-specific validation.

Do not describe the local authority source as identity-provider authentication
or claim that mocked connector tests establish real-world deployment efficacy.

Avoid unbounded claims such as “the project solves agent identity security,” “prevents privilege escalation,” or “is enterprise-ready.”

Do not manufacture adoption, testimonials, issue activity, benchmark scale, or external validation. Preserve genuine criticism and independently submitted issues.
