## MODIFIED Requirements

### Requirement: Human triage workflow

Vigilante SHALL support authorized human operators in triaging suspicious cases through review, escalation, dismissal, and follow-up states, while read-only users cannot change case or reporting state.

#### Scenario: Operator reviews active case

- **GIVEN** an operator with case mutation permission opens an active case
- **WHEN** the evidence and risk context are reviewed
- **THEN** the operator can decide whether to escalate, archive, or continue follow-up

#### Scenario: Read-only user attempts case triage

- **GIVEN** an authenticated read-only user
- **WHEN** the user attempts to change case status, generate a report, or initiate enforcement
- **THEN** the system returns `403` without changing case state or triggering an external side effect

### Requirement: Organization scoped visibility

Vigilante SHALL scope case visibility to the authenticated user's organization or explicitly authorized network context.

#### Scenario: Dealer user lists cases

- **GIVEN** a dealer-scoped user is authenticated
- **WHEN** the user requests case data
- **THEN** the response contains only cases visible to that dealer context

#### Scenario: Network viewer lists cases

- **GIVEN** an explicitly authorized network viewer is authenticated
- **WHEN** the user requests case data
- **THEN** the response may contain cases across the Yamaha network without granting mutation authority
