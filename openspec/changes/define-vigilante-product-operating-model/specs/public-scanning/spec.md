## ADDED Requirements

### Requirement: Public scan value boundary

Vigilante SHALL treat public Places scanning as the primary currently reliable
source for detecting cloned or suspicious public listings.

#### Scenario: Suspicious public listing is detected

- GIVEN an authorized scan target
- WHEN public Places results indicate a suspicious nearby listing
- THEN the system creates or updates an operational case with traceable source context

### Requirement: Public scan uncertainty

Vigilante SHALL make public scan uncertainty explicit when evidence is
insufficient for a final decision.

#### Scenario: Public result is ambiguous

- GIVEN a public scan result resembles an authorized dealer but lacks decisive evidence
- WHEN the result is shown to an operator
- THEN the system preserves it as a reviewable case instead of treating it as confirmed fraud
