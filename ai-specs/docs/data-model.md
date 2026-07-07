# Vigilante Domain Model

This is a compact model map for agents and OpenSpec context. Code remains the
source of truth in `app/models.py` and repository behavior in `app/store.py`.

## Core Concepts

- Organization: platform, network, dealer, or related operating unit.
- Dealer or branch: protected public business location.
- Threat case: operational case for suspected impersonation, clone, manipulated
  media, phishing, or related public listing risk.
- Evidence artifact: source-bound material attached to a case with provenance.
- Alert event: notification or operational signal emitted for a case.
- GBP connection: organization-level Google Business Profile connection and
  location binding.
- Browser session or run: experimental guided browser automation state.

## Invariants

- Cases must stay scoped to the correct organization.
- Evidence must keep source, provenance, and case association.
- Demo data must not seed production.
- Browser capture must remain distinguishable from official GBP evidence.
- Reports and enforcement actions must preserve human approval.
