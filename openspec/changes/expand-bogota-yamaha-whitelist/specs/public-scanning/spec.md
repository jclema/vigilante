## MODIFIED Requirements

### Requirement: Public scan value boundary

Vigilante SHALL treat public Places scanning as the primary currently reliable
source for detecting cloned or suspicious public listings.

#### Scenario: Suspicious public listing is detected

- GIVEN an authorized scan target
- WHEN public Places results indicate a suspicious nearby listing
- THEN the system creates or updates an operational case with traceable source context

#### Scenario: Bogotá official dealers are added to public scan coverage

- GIVEN Incolmotos Yamaha publishes official Bogotá Tienda Yamaha points
- WHEN the whitelist sync filters department `11`, city aliases `Bogotá D.C.` and `Bogotá. D.C.`, and `tienda = SI`
- THEN Vigilante creates authorized dealer entries and public-scan profiles for the official Bogotá points

### Requirement: Official Yamaha whitelist provenance

Vigilante SHALL preserve source provenance when importing official Yamaha dealer
coverage from Incolmotos.

#### Scenario: Official Bogotá row has seven-digit fixed phones

- GIVEN an official Bogotá row includes a seven-digit fixed phone
- WHEN the row is normalized into the whitelist
- THEN the fixed phone uses the Bogotá area code `601`

#### Scenario: City aliases differ by punctuation

- GIVEN official rows use both `Bogotá D.C.` and `Bogotá. D.C.`
- WHEN the importer filters Bogotá
- THEN both variants are accepted and stored under canonical city `Bogotá D.C.`
