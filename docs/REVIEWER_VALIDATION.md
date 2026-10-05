# Reviewer experience validation — 0.20.0

Maintainer evaluation on 2026-10-03. This is not independent adoption or production
certification. Earlier model success and failure runs remain documented in
[LIVE_LAB_VALIDATION.md](LIVE_LAB_VALIDATION.md).

## What changed

- A single local launcher initializes or upgrades lab state, prepares the model,
  starts Docker services and opens a private sign-in link.
- The live lab's welcome screen explains the purpose, local execution and synthetic
  data. It no longer asks the reviewer to select an operator key file.
- Sign-in codes expire in 10 minutes and are single use. Only their hashes are
  stored. Browser sessions last one hour and are invalidated by gateway restart.
- Operator keys stay server-side. Sessions use HttpOnly, SameSite=Strict cookies,
  request tokens and exact same-origin checks. Signed API clients remain supported.
- A separate worker container runs the agent. Its fixed control API has no shell,
  arbitrary prompts, arbitrary destination URLs or Docker socket access.
- Browser controls cover scenario setup, investigation, proposal review, exact
  approved execution and fresh login verification. Activity refreshes automatically.

## Automated checks

**168 tests passed**; **2,391 SQLite connections opened, 0 unclosed**.
Eight new tests cover single-use sign-in, expiration, logout and session restore,
CSRF and foreign-origin denial, role separation, the public landing page, the
complete guided workflow, and revocation after approval.

The guided HTTP integration test uses a deterministic model double against real
identity, portal, operations, gateway, scenario and worker HTTP servers. Its
operator approves automatically. It is not a claim of live-model reliability.

## Live Docker guided run

The local launcher started all services successfully. A one-time-code exchange
created a session, and the guided start endpoint launched the isolated Ollama
qwen3:1.7b worker. It proposed the correct repair after two model calls. An automated
test operator checked and approved the exact configuration; the guided resume
endpoint applied it, and guided verification returned a successful fresh login.
This exercised the guided APIs, not clicks in a signed-in browser. Machine-readable
results: [reviewer-0.20.0.json](evaluations/reviewer-0.20.0.json).

Source and wheel builds, JavaScript syntax and internal documentation links passed.

## UI verification and limitations

The refreshed public landing page was inspected in the in-app browser. The
no-upload explanation and launcher instructions were visible. A screenshot was
captured at the existing narrow window size. The first browser accessibility
inspection stalled; subsequent DOM and viewport inspection succeeded.

Signed-in browser interactions have not been visually verified. Earlier browser
credential permission restrictions were respected. Session and guided-action APIs
were tested directly; those results do not replace full visual usability testing.

The initial setup still requires Python, Docker and a terminal command. The first
model download can be large. This is a guided local lab, not a hosted service.
Interrupted or uncertain operations require inspection rather than an automatic
retry. Advanced recovery and the optional delegated-helper flow remain terminal
workflows. Multiple simultaneous reviewers share one local scenario.

Hosted GitHub CI has not been run for this source state. No new release has been
published to GitHub by this update.
