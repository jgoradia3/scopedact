# Vision

ScopedAct explores a provider-neutral authority and accountability layer for agent tool workflows. An agent should receive only the authority needed for its assigned task. Enforcement should occur outside the model, delegation should not expand that authority, and protected actions should remain attributable and subject to operator intervention.

The live incident lab and scripted ticket pilot are reference workflows, not the definition of the project. Their synthetic services make the authorization boundary reproducible without organizational credentials. The live walkthrough currently uses Ollama; the core authorization checks do not depend on the model provider.

Identity and authority are distinct. Identity establishes who or what is making a request; authority establishes what that caller may do for this task. The current implementation uses independent HMAC role keys as development identities and exact action/resource grants as authority. It does not claim enterprise identity assurance or inference of intent from natural language.

The current objective is a small, testable reference implementation with explicit failure and trust boundaries. Broader integrations should follow concrete external evaluation needs. See [capabilities](docs/CAPABILITIES.md) and [roadmap](docs/ROADMAP.md); future mechanisms must not be represented as implemented or validated.
