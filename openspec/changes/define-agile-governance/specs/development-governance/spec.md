## ADDED Requirements

### Requirement: Risk-based development governance

Vigilante SHALL classify contribution process requirements by change risk so
low-risk work stays lightweight and high-risk work receives stronger controls.

#### Scenario: Contributor makes a docs-only change

- GIVEN a contributor updates a low-risk documentation page
- WHEN they open a pull request
- THEN the process allows a short PR without requiring a full OpenSpec change

#### Scenario: Contributor changes evidence behavior

- GIVEN a contributor changes evidence display, provenance, or case behavior
- WHEN they open a pull request
- THEN the process requires an OpenSpec change or updated spec, verification, and risk notes

### Requirement: Protected main with short-lived work branches

Vigilante SHALL keep `main` protected while normal development happens in
short-lived branches reviewed through pull requests.

#### Scenario: Developer starts new work

- GIVEN a developer wants to implement a change
- WHEN the work begins
- THEN the developer creates a focused branch instead of committing directly to `main`
