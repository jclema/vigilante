# product-positioning Specification

## Purpose

Define Vigilante's market, user, and operating model requirements.

## Requirements

### Requirement: Spec-driven product operating model

Vigilante SHALL maintain product intent, target users, constraints, acceptance
criteria, and measurable outcomes in repo-local specs before implementing
non-trivial product changes.

#### Scenario: New market opportunity is explored

- GIVEN a new opportunity around fraud in Maps, GBP, or Places
- WHEN the team wants to turn it into product work
- THEN the work is captured or enriched through OpenSpec before implementation tasks are started

### Requirement: Human-reviewed enforcement boundary

Vigilante SHALL position itself as an operations and evidence product where
humans approve irreversible reports or enforcement actions.

#### Scenario: High-risk case is ready for escalation

- GIVEN a case has high risk and supporting evidence
- WHEN an external report or enforcement action is considered
- THEN the system presents evidence and recommendation context without bypassing human approval
