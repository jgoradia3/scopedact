# Screenshot provenance and reproduction

The README images are browser screenshots of a read-only documentation report generated from a fresh run of the actual v0.14.1 ticket pilot on 2026-09-30. The report is not an operator dashboard or a proposed product interface.

## What was run

`tools/build_demo_report.py` starts the existing gateway and synthetic ticket backend on ephemeral loopback ports. Independently keyed scripted clients exercise an assigned child read, an unassigned-ticket denial, an update held for approval, operator approval of its digest, execution of that same request, and parent revocation followed by a denied child read. The script asserts the decisions and resulting ticket state before generating the report.

It calls the same authenticated APIs used by the pilot CLI. The report renders selected response fields and the recorded lineage rows; it does not invent decisions. Generated task IDs, credentials, databases, and raw audit exports are not published. Screenshot captions and field labels explain the results; no output has been retouched.

This local run does not test Docker isolation. The separately documented hosted Docker evaluations cover the supplied container topology. The harness holds several role keys, so it is a trusted evaluator, not an untrusted agent runtime.

## Reproduce locally

From the repository root after installing the package:

```sh
python tools/build_demo_report.py
python -m http.server 8899 --bind 127.0.0.1 --directory pilot-results/demo-report
```

Open `http://127.0.0.1:8899/` for decisions and `http://127.0.0.1:8899/lineage.html` for delegation and intervention. Capture these pages in your browser. `results.json` contains the selected results behind the report. Stop the static server with Ctrl+C.

Keys and databases exist only in a temporary directory and are removed when the scenario completes; both pilot services are stopped. HTML and selected result excerpts are written to the ignored `pilot-results/` directory. The report contains only synthetic ticket information.

## Included captures

- [Decisions and approval](images/pilot-decisions.png)
- [Delegation and revocation](images/pilot-lineage.png)

The existing v0.14.1 source ZIP remains the original reviewed artifact. These documentation assets and the reproduction helper are a subsequent presentation update on `main`, not a new engine release.
