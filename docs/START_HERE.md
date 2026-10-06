# Documentation guide

Start with **one investigation**. You do not need to work through every older demonstration.

| What you want to do | Read this |
|---|---|
| Install and open the console without Docker | [Native review](NATIVE_REVIEW.md) |
| Understand what to click and what results mean | [Reviewer walkthrough](REVIEWER_QUICKSTART.md) |
| Watch before installing | [Narrated demo](DEMO_VIDEO.md) |
| Run the isolated Docker lab | [Live incident lab](LIVE_INCIDENT_LAB.md) |
| Report a reproducible finding | [Technical review guide](REVIEW_GUIDE.md) |
| Understand trust and access boundaries | [Threat model](THREAT_MODEL.md), [local security](LOCAL_SECURITY_BOUNDARY.md) |
| Inspect implementation and limits | [Architecture](ARCHITECTURE.md), [capabilities](CAPABILITIES.md), [limitations](LIMITATIONS.md) |
| Check what was actually tested | [Validation record](STABILIZATION_REVIEW.md), [control-to-test map](CONTROL_TEST_MAP.md), [evidence guidance](EVIDENCE.md) |
| Build an integration | [Connector contract](CONNECTOR_DEVELOPMENT.md), [process-local SDK](SDK_INTEGRATION.md) |
| Contribute or prepare a release | [Contributing](../CONTRIBUTING.md), [release checklist](GITHUB_RELEASE.md) |

## Separate evaluation paths

The current incident lab uses a local model and live synthetic services. The
[ticket pilot](TICKET_PILOT.md) and [delegation evaluation](DELEGATION.md) use scripted
clients for repeatable control checks. They are useful additional tests, not prerequisites.
See [real versus simulated](REAL_VS_SIMULATED.md) for the distinction.

The [managed document workspace](WORKSPACE.md), [document incident](INCIDENT_EVALUATION.md),
[document agent](LOCAL_AGENT.md), [file workspace](APPLICATION_GUIDE.md), and
[procurement lab](SERVICE_BOUNDARY_LAB.md) remain supported reference examples.
Their data, authentication and isolation boundaries differ. Do not combine their
setup commands with the live incident lab.

## Historical evidence

[Release history](RELEASE_HISTORY.md) and versioned validation documents preserve
past results. Their counts and deployment statements describe those runs only.
[Changelog](../CHANGELOG.md) summarizes changes; [research context](PROBLEM_AND_EVIDENCE.md)
and [research mapping](RESEARCH_TO_IMPLEMENTATION.md) explain the broader motivation.

## Repository files

`src/` contains the implementation; `tests/` protects existing behavior. `tools/`
and `pilot/` contain launchers and deployment checks. `config/` and `examples/`
support the optional legacy CLI and SDK examples; they are not settings for the
current incident console. `audit/` is an output location for older CLI examples,
not evidence from a reviewer. The package metadata, Dockerfiles, Compose files and
CI workflow remain necessary for the documented installation and evaluation paths.
