## MODIFIED Requirements

### Requirement: Human triage workflow

Vigilante SHALL support human triage of suspicious cases through review,
escalation, dismissal, and follow-up states.

#### Scenario: Operator reviews active case

- GIVEN an operator opens an active case
- WHEN the evidence and risk context are reviewed
- THEN the operator can decide whether to escalate, archive, or continue follow-up

### Requirement: Territory coverage visibility

Vigilante SHALL make official monitored coverage visible by city in dashboard
filters, territory summaries, and trust views.

#### Scenario: Bogotá dealers exist in the whitelist

- GIVEN official Bogotá Yamaha dealers are loaded with public-scan profiles
- WHEN an operator opens the dashboard
- THEN Bogotá appears in monitored coverage, filters, and city-level trust summaries

#### Scenario: Bogotá city spelling varies

- GIVEN source data or cases contain `Bogota`, `Bogota D.C.`, `Bogotá D.C.`, or `Bogotá. D.C.`
- WHEN the dashboard renders city labels
- THEN the operator sees the canonical label `Bogotá D.C.` when the city refers to Bogotá D.C.
