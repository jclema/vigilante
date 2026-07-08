## ADDED Requirements

### Requirement: Evidence provenance

Vigilante SHALL preserve the source, case association, and reliability context of
evidence artifacts.

#### Scenario: Evidence is attached to a case

- GIVEN a case receives a source artifact
- WHEN the artifact is stored or displayed
- THEN the system keeps enough provenance for an operator to understand where it came from and how reliable it is

### Requirement: Browser capture limitation

Vigilante SHALL distinguish experimental browser capture from official GBP
evidence.

#### Scenario: Browser capture is available

- GIVEN a browser automation run captures a public Maps page
- WHEN the artifact is attached to a case
- THEN the system does not present it as authoritative GBP customer media
