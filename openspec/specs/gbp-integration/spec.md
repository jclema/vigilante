# gbp-integration Specification

## Purpose

Define Google Business Profile connection, customer media access, and fallback
behavior.

## Requirements

### Requirement: GBP access state visibility

Vigilante SHALL show GBP connection and customer media access state in a way
that distinguishes software readiness from external Google approval blockers.

#### Scenario: Customer media access is blocked

- GIVEN a GBP connection exists but Google has not granted operational customer media access
- WHEN an admin reviews the connection
- THEN the system communicates the blocker without implying that code changes alone can resolve it

### Requirement: GBP fallback path

Vigilante SHALL support product planning for manual or semi-automated evidence
fallbacks while official GBP access is blocked.

#### Scenario: Official media cannot be fetched

- GIVEN official GBP media access is unavailable
- WHEN a case requires visual validation
- THEN the workflow can route to a human-reviewed fallback instead of relying on unstable cloud browser scraping
