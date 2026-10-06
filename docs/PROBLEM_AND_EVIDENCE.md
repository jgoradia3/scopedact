# Why task authority and execution evidence matter

ScopedAct addresses a practical review question: when an agent carries out a multi-step assignment, can an operator constrain its protected actions and reconstruct what happened under that authority?

## Evidence behind the problem

| Source | What it establishes | Relevance to ScopedAct |
|---|---|---|
| [OWASP LLM06:2025 — Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | Too much functionality, permission or autonomy can enable damaging actions following unexpected or manipulated model output. It recommends downstream authorization and limited permissions. | Explicit resource/action grants and authorization outside the model. |
| [AgentDojo — NeurIPS 2024, Datasets and Benchmarks](https://proceedings.nips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | A peer-reviewed evaluation environment tests tool-using agents against malicious instructions in untrusted data. It reports both task failures and security failures. | Evaluate useful behavior and protected execution separately; an agent may fail without an attack. ScopedAct does not claim AgentDojo benchmark results. |
| [NIST — Strengthening AI Agent Hijacking Evaluations, January 2025](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations) | A government technical evaluation describes agent hijacking through external data and emphasizes adaptive, task-specific testing. | A staged misleading-log exercise is one bounded evaluation, not proof of general resistance to prompt injection. |
| [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Application logging needs context and identifiers connecting related events from one interaction. | Task-linked requests, callers, decisions and execution outcomes make the protected activity inspectable together. |

The NeurIPS paper is peer-reviewed research; NIST is a government technical report/blog; OWASP provides practitioner guidance. They are different kinds of evidence, not endorsements of this project.

## The operational questions

- **Excess authority:** does the agent's general access exceed what this assignment requires?
- **Untrusted instructions:** can retrieved content induce a request that policy should reject?
- **Attribution through delegation:** can a helper receive more authority than its parent, and can its actions be traced back?
- **Fragmented records:** can a reviewer connect the task, acting agent, permission decision and tool result?
- **Intervention:** can remaining authority be revoked after work has begun?
- **Ambiguous outcomes:** was a change merely proposed, approved, executed, or independently checked for recovery?

The reconstruction problem is our engineering motivation, consistent with the logging guidance above. We do not claim a measured industry-wide increase in log-review difficulty, a measured reduction in review time, or a unique invention of event correlation.

## What the demonstration establishes

The supplied lab demonstrates a subset of these concerns through synthetic services and actual gateway requests. Exact permissions enforce scope; prompt text alone does not. The local model chooses requests, and recorded outcomes may differ across runs. The activity map shows requests that traverse the gateway, not every host action or hidden model reasoning.

The current system does not implement enterprise identity integration, semantic proof of task necessity, universal prompt-injection prevention, or immutable external audit evidence. Independent evaluations and broader deployments are needed before making claims about real organizational impact.
