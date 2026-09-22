# Vision

ScopedAct explores a provider-neutral authority and accountability layer for agent tool workflows. An agent should receive only the authority needed for its assigned task. Enforcement should occur outside the model, delegation should not expand that authority, and protected actions should remain attributable and subject to operator intervention.

The ticket pilot is one reference workflow, not the definition of the project. Its synthetic backend makes the authorization boundary reproducible without requiring organizational credentials or a particular model provider.

Identity and authority are distinct. Identity establishes who or what is making a request; authority establishes what that caller may do for this task. The current pilot uses independent HMAC role keys as development identities and exact action/resource grants as authority. It does not claim enterprise identity assurance or inference of intent from natural language.

The current objective is a small, testable reference implementation with explicit failure and trust boundaries. Broader integrations should follow concrete external evaluation needs. See the capability table and roadmap; future mechanisms must not be represented as implemented or validated.
