## MODIFIED Requirements

### Requirement: Evidence provenance

Vigilante SHALL preserve the source, case association, reliability label, and
retrieval context of evidence artifacts.

#### Scenario: Evidence is attached to a case

- GIVEN a case receives a source artifact
- WHEN the artifact is stored or displayed
- THEN the system keeps enough provenance for an operator to understand where it came from and how reliable it is

#### Scenario: Official GBP customer media is attached

- GIVEN an official GBP customer media item is attached to a case
- WHEN an operator reviews the evidence
- THEN the system shows the GBP location context, retrieval timestamp, source identifier, and reliability label

### Requirement: Browser capture limitation

Vigilante SHALL distinguish experimental browser capture from official GBP
evidence.

#### Scenario: Browser capture is available

- GIVEN a browser automation run captures a public Maps page
- WHEN the artifact is attached to a case
- THEN the system does not present it as authoritative GBP customer media

### Requirement: Manipulated storefront photo review

Vigilante SHALL support evidence review for customer-uploaded storefront photos
suspected of AI manipulation or fraudulent phone-number insertion.

#### Scenario: Suspicious customer photo includes a fake phone number

- GIVEN an authorized Yamaha dealer has a customer-uploaded GBP photo suspected of showing a fake phone number on the facade
- WHEN the photo is reviewed as case evidence
- THEN the operator can see the source, dealer/location context, suspected manipulation reason, and required human decision path
