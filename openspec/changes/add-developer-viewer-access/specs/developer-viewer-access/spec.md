## ADDED Requirements

### Requirement: Explicit developer viewer provisioning

Vigilante SHALL grant developer viewer access only to an explicitly provisioned, active user membership associated with the user's normalized Google email.

#### Scenario: Provisioned developer signs in

- **GIVEN** an active developer viewer membership exists for a normalized email
- **WHEN** that person signs in with the matching Google account
- **THEN** the system links the Google identity and grants developer viewer access

#### Scenario: Unprovisioned Google user signs in

- **GIVEN** no active membership exists for a Google email
- **WHEN** that person signs in
- **THEN** the system does not grant access to Yamaha network data

### Requirement: Network-wide read-only visibility

Vigilante SHALL allow a developer viewer to inspect Yamaha network dashboards, cases, and authorized evidence across organizations without granting mutation authority.

#### Scenario: Developer viewer inspects operations

- **GIVEN** an authenticated developer viewer
- **WHEN** the user opens a dashboard, case, or authorized evidence view
- **THEN** the system returns the network-visible read-only experience

### Requirement: Developer mutations fail closed

Vigilante MUST deny developer viewers all state-changing product, configuration, integration, reporting, enforcement, and administration operations.

#### Scenario: Developer attempts a state-changing request

- **GIVEN** an authenticated developer viewer
- **WHEN** the user submits a request that changes application or external state
- **THEN** the system returns `403` without changing state or triggering an external side effect

### Requirement: Sensitive operational resources remain inaccessible

Vigilante MUST deny developer viewers access to secrets, credentials, raw browser session state, membership administration, notification destinations, and integration configuration.

#### Scenario: Developer requests sensitive settings

- **GIVEN** an authenticated developer viewer
- **WHEN** the user requests a sensitive settings page or API
- **THEN** the system returns `403` without disclosing the protected resource

### Requirement: Access can be revoked independently

Vigilante SHALL allow an operator to deactivate or remove developer viewer access without changing source code, application secrets, or Google Cloud IAM.

#### Scenario: Developer access is revoked

- **GIVEN** a previously provisioned developer viewer
- **WHEN** the membership is removed or the user is deactivated
- **THEN** subsequent sessions cannot access Yamaha network data
