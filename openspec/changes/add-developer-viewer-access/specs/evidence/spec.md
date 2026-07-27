## ADDED Requirements

### Requirement: Authenticated evidence delivery

Vigilante MUST require authentication and organization or network visibility before returning evidence media.

#### Scenario: Authorized viewer requests evidence

- **GIVEN** an authenticated user can view the case or organization associated with an evidence artifact
- **WHEN** the user requests the evidence media
- **THEN** the system returns the artifact without exposing storage credentials or browser session state

#### Scenario: Unauthorized user requests evidence

- **GIVEN** a user is unauthenticated or cannot view the associated case or organization
- **WHEN** the user requests the evidence media
- **THEN** the system returns `401`, `403`, or `404` without returning the artifact
