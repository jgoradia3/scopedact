# Technical-review invitation template

Subject: Technical feedback on ScopedAct's agent authorization controls

I'm developing ScopedAct, an open-source authorization and accountability reference
implementation. It checks agent tool requests before execution and records allowed,
denied, approved and completed actions by task.

Would you be willing to evaluate one control or integration concern? The
[walkthrough](DEMO_VIDEO.md) shows the experience before installation. The
[native setup](NATIVE_REVIEW.md) runs a local model and synthetic incident on your own
computer; Docker is optional. The separate [ticket pilot](TICKET_PILOT.md) offers
scripted, reproducible control checks without a model.

I'm interested in specific weaknesses: whether denials prevent execution, approval
binds the exact change, revocation prevents later calls, and the evidence is useful.
The [review guide](REVIEW_GUIDE.md) explains what to record. An incomplete investigation
or a usability problem is useful feedback; no positive endorsement is requested.

Please include the commit, environment and what you actually tested. Sensitive
vulnerabilities should follow [security reporting](../SECURITY.md).

---

Adapt links to the published commit before sending. Obtain permission before publicly
attributing feedback. This template does not establish independent use or endorsement.
