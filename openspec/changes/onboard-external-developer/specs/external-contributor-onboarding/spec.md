## ADDED Requirements

### Requirement: English onboarding entrypoint

Vigilante SHALL provide an English onboarding entrypoint that explains product
scope, current state, architecture, setup, SDD workflow, and contribution rules
for an external developer.

#### Scenario: Developer joins without prior context

- GIVEN an external developer has repository access
- WHEN they start onboarding
- THEN they can follow a documented reading order and local setup path without relying on verbal context

### Requirement: Staged access boundary

Vigilante SHALL define staged access expectations that keep production secrets,
customer evidence, cloud permissions, and service accounts unavailable during
initial onboarding.

#### Scenario: Developer starts first week

- GIVEN the developer has not completed a first safe contribution
- WHEN they begin project work
- THEN the documented access policy limits them to repository and local demo workflows

### Requirement: Safe first contribution

Vigilante SHALL provide a first-contribution brief that points new developers to
a low-risk, spec-backed task.

#### Scenario: Developer selects first task

- GIVEN the developer has completed required reading
- WHEN they choose their first implementation task
- THEN the brief directs them toward a small, testable slice that does not require production access
