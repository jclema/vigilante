## ADDED Requirements

### Requirement: Visibility does not imply mutation authority

Vigilante MUST evaluate read visibility separately from application, organization, integration, and platform mutation permissions.

#### Scenario: Network viewer accesses operational dashboards

- **GIVEN** a network-wide read-only user
- **WHEN** the user requests authorized dashboards and product views
- **THEN** the system returns those views without granting settings or mutation permissions

#### Scenario: Network viewer invokes an operational action

- **GIVEN** a network-wide read-only user
- **WHEN** the user invokes a scan, notification, integration, membership, reporting, or enforcement action
- **THEN** the system returns `403` before performing the action
