> Legacy evaluation paths. For the current authenticated ticket pilot, use [the reviewer guide](REVIEW_GUIDE.md), [architecture](ARCHITECTURE.md), and [capability matrix](CAPABILITIES.md). The descriptions below apply only to the older workspace/laboratory examples.

# Real code versus simulation

| Element | Status | Meaning |
| --- | --- | --- |
| Exact action-resource evaluation | Implemented | The gateway makes enforceable allow/deny decisions. |
| Signed agent HTTP requests | Implemented | Method, path, timestamp, nonce, and body digest are integrity-checked. |
| Replay, expiration and lifecycle checks | Implemented | Invalid requests are blocked before tool execution. |
| Manual approval and operator controls | Implemented | Dashboard decisions change durable gateway behavior. |
| Gateway-to-tool HTTP call | Implemented | Allowed actions cross a separate protocol boundary. |
| Durable state and event evidence | Implemented | SQLite and hash-chained events survive process restarts. |
| Invoice and purchase-order records | Synthetic | No real business records are used. |
| Payment | Synthetic | `executed=True` changes only local demonstration data. |
| Default AI reasoning | Scripted | Requests are deterministic; optional model proposals remain staged. |
| Human and agent identity | Development identifiers | No corporate IdP or workload identity is integrated. |
| Enterprise deployment | Not implemented | Local HTTP threads are not production workload isolation. |

The prototype is valuable because the control behavior is executable and reviewable. It must not be presented as a deployed enterprise product or real payment-security system.
