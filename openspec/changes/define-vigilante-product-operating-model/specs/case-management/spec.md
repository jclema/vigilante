## ADDED Requirements

### Requirement: Human triage workflow

Vigilante SHALL support human triage of suspicious cases through review,
escalation, dismissal, and follow-up states.

#### Scenario: Operator reviews active case

- GIVEN an operator opens an active case
- WHEN the evidence and risk context are reviewed
- THEN the operator can decide whether to escalate, archive, or continue follow-up

### Requirement: Organization scoped visibility

Vigilante SHALL scope case visibility to the authenticated user's organization
context.

#### Scenario: Dealer user lists cases

- GIVEN a dealer-scoped user is authenticated
- WHEN the user requests case data
- THEN the response contains only cases visible to that dealer context
