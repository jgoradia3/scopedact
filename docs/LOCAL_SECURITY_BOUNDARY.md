# Public repository, private local lab

Publishing ScopedAct on GitHub publishes source and static media. It does not publish
your running console, establish a connection to your laptop, or give repository
visitors access to your files. A reviewer who downloads the source runs a separate
lab with their own generated credentials on their own machine.

## What is protected in the supplied setup

- **Local endpoints:** the Docker console is published on `127.0.0.1:8891`.
  Native services bind to loopback. No public tunnel is part of the setup.
- **Console authentication:** private single-use sign-in codes expire after ten
  minutes. Sessions expire after one hour; the operator signing key stays out of
  the browser. Session cookies use HttpOnly and SameSite=Strict, with CSRF tokens.
- **Browser boundary:** Host and Origin checks reject unexpected origins. Console
  assets use a restrictive content-security policy. These supplement authentication.
- **Limited model tools:** the supplied agent can request configured document reads
  and propose updates; the workspace path also supports constrained discovery. It
  is not offered a shell, arbitrary code execution or unrestricted URL fetching.
  Unknown tools and invalid arguments are rejected. A prompt cannot add a tool.
- **Independent authorization:** task permissions, expiration, intervention and
  approval checks run outside the model, before protected connector execution.
  Approval does not grant access beyond the task or override later revocation.
- **Docker boundaries:** the agent network is internal, protected services are on
  separate networks, and no Docker socket or personal home directory is mounted.
  Supplied application containers have read-only roots, dropped capabilities and
  no-new-privileges. Necessary lab state remains writable. The model container has
  a writable model volume/root and is not a read-only application container.
- **Publication separation:** generated keys, lab databases and journals are excluded
  from normal source packaging and Docker build context. Ignore rules are safeguards,
  not substitutes for reviewing commits. Public CI uses GitHub-hosted Ubuntu runners,
  not the maintainer's laptop.

## Prompt injection: what it can and cannot establish

Malicious text can cause a model to request the wrong action. The lab deliberately
includes such a test. That does not itself create an operating-system capability:
requests still pass through the implemented tool parser and authorization gateway.
However, injection can influence actions already within the permitted scope,
produce a misleading proposal, or waste computation. Human approval requires
inspection; authorization does not establish that a proposed repair is correct.

These controls do not prove the absence of vulnerabilities in Python, the gateway,
connectors, Ollama, Docker, the browser or the operating system. ScopedAct is not a
complete hostile-code sandbox or universal prompt-injection defense.

## Native mode has a different boundary

Native mode runs the trusted lab services under the same OS account. It binds locally
and authenticates API requests, but it does not isolate those processes from other
files accessible to that account. A process-level compromise could therefore have
broader consequences than a rejected model tool call. Use synthetic data; use a
separate disposable VM when evaluating untrusted code or changes. Docker improves
the supplied separation but is not a promise of immunity from host compromise.

## Keep your own laptop out of the reviewer path

Give reviewers the public repository and video, not a tunnel into your machine.
Keep the default loopback bindings, do not forward ports or mount personal/cloud
credential directories into the lab, and do not execute unreviewed pull-request
code on a machine holding valuable credentials. A GitHub issue or fork does not
execute locally unless someone runs its contents.

Stop services when finished: Ctrl+C in a native launcher, or the documented Docker
Compose stop/down command for that lab. Do not delete evidence unless intended.
Do not share sign-in codes, keys, private journals or raw databases.

## Maintainer check — October 5, 2026

Observed Docker console bindings were loopback on ports 8890 (older workspace) and
8891 (incident lab); observed native test and Ollama listeners were also loopback.
The running incident services had no privileged containers, no Docker socket mount,
and no personal-directory bind mounts outside dedicated lab state and keys.

The incident console returned 401 for an unauthenticated task request, 403 for a
cross-origin console login, and 403 for an untrusted Host header. The disposable
agent boundary probe passed checks against backend DNS names and concrete container
IPs, privileged mounts and operator routes.

A comparison of 48 generated local keys against 241 reachable repository-history
blobs smaller than 2 MB found no exact matches. This is a limited check, not a full
secret-detection audit: it does not cover unknown past credentials, every binary,
all screenshots or unrelated accounts. Runtime keys were not printed or uploaded.

This review covers the repository and observed lab configuration, not the laptop's
router, every background process, other applications, or a complete penetration test.
