# Draft technical-review invitation

Subject: Independent technical feedback on ScopedAct's agent authorization controls

Hi [name],

I'm developing ScopedAct, an open-source developer preview that places task-scoped authorization and human approval between an agent's proposed action and a protected tool.

Would you be willing to run the isolated support-ticket pilot with synthetic data or review one control? I'm especially interested in bounded delegation, approval binding, concurrent replay prevention, parent revocation behavior, and whether action lineage and execution evidence are useful and accurate.

Release: [insert published release link]
Reviewer guide: [insert guide link]

The Docker pilot includes a real REST workflow, separate primary/child/operator credentials, exact-content approval, revocation, and evidence export. It uses synthetic tickets and does not require a paid model or cloud account. The guide lists the tested behavior and remaining limitations. A useful review could be as small as reproducing one workflow and reporting a specific weakness or integration obstacle. I am asking for candid technical feedback, not an endorsement.

If you share findings, please note the version, environment, and what you tested. Please use the security-reporting channel for sensitive issues.

Thank you,
Jay

---

Replace placeholders before sending. Record feedback and attribute it publicly only with the reviewer's permission. No invitations have been sent automatically.
