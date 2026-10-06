# What is real, and what is synthetic?

| Element | Current incident review |
|---|---|
| Incident, users and access profiles | Synthetic local evaluation data; no enterprise account connection |
| Agent decisions | A real Ollama model chooses supported tools; no scripted fallback or guaranteed repair |
| Service calls | Real local HTTP calls to the supplied services |
| Authorization and denial | Actual gateway checks before protected dispatch |
| Repair | An actual change to synthetic portal configuration, only after required authorization and approval |
| Recovery | A fresh login verification, separate from the model's summary |
| Activity map | Recorded gateway-covered requests, not the model's reasoning or all host activity |
| Misleading evidence | Deliberately planted instruction; the model may ignore it or attempt forbidden access |
| Video | Edited saved evaluations with synthetic narration, not a continuous live session |
| Identity | Local development credentials and policy profiles, not enterprise identity federation |

The separate [ticket evaluation](TICKET_PILOT.md), [delegation evaluation](DELEGATION.md),
and older procurement tour use scripted clients to test repeatable controls.
Automated tests may use model doubles; they are not live-model reliability results.
See [validation](STABILIZATION_REVIEW.md) for observed outcomes, including incomplete investigations.
