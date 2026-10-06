# Choose a Docker evaluation

For the current reviewer console, use the **[live incident lab](LIVE_INCIDENT_LAB.md)**.
For a Docker-free installation, use [native review](NATIVE_REVIEW.md).

| Compose file | Purpose | Model required? |
|---|---|---|
| `compose.lab.yaml` | Current live-service incident investigation and reviewer console | Yes for the agent walkthrough; separate scripted control evaluation also available |
| `compose.pilot.yaml` | Ticket approval, delegation, replay and recovery checks | No; scripted clients |
| `compose.workspace.yaml` | Managed-document investigation and boundary probes | Only for the optional local-agent path |
| `compose.yaml` | Older offline procurement tour | No; scripted |

Use the commands in the corresponding [lab](LIVE_INCIDENT_LAB.md),
[ticket](TICKET_PILOT.md), or [workspace](WORKSPACE.md) guide. These are separate
scenarios, not interchangeable launch configurations. The root Dockerfile is also
used by the service deployments; its default command alone runs the offline tour.

Keep published ports on loopback. Docker adds the documented network and filesystem
separation, but the host administrator remains trusted. See [local security](LOCAL_SECURITY_BOUNDARY.md).
