## ADDED Requirements

### Requirement: Production operating context

Vigilante SHALL keep production deployment, health, rollback, and security
checks documented with exact operational commands.

#### Scenario: Production incident is investigated

- GIVEN WatchmanHub production is degraded
- WHEN an operator starts first response
- THEN the runbook provides concrete health, readiness, service, log, and rollback commands

### Requirement: Production safety boundary

Vigilante SHALL preserve production safety controls when changing app config,
infrastructure, authentication, or deployment behavior.

#### Scenario: Deployment behavior changes

- GIVEN a change affects production routing, secrets, IAM, Cloud Run, Scheduler, or Cloud Armor
- WHEN the change is specified
- THEN the spec and tasks include verification and rollback criteria
