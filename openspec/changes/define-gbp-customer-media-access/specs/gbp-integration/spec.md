## MODIFIED Requirements

### Requirement: GBP access state visibility

Vigilante SHALL show GBP connection and customer media access state in a way
that distinguishes software readiness from external Google approval, permission,
scope, and quota blockers.

#### Scenario: Customer media access is blocked

- GIVEN a GBP connection exists but Google has not granted operational customer media access
- WHEN an admin reviews the connection
- THEN the system communicates the blocker without implying that code changes alone can resolve it

#### Scenario: API quota is zero

- GIVEN the Google Business Profile API quota for the project is `0`
- WHEN an operator reviews customer media access state
- THEN the system identifies the state as an access approval blocker instead of retrying as a transient integration failure

### Requirement: GBP fallback path

Vigilante SHALL support product planning for manual or semi-automated evidence
fallbacks while official GBP access is blocked.

#### Scenario: Official media cannot be fetched

- GIVEN official GBP media access is unavailable
- WHEN a case requires visual validation
- THEN the workflow can route to a human-reviewed fallback instead of relying on unstable cloud browser scraping

### Requirement: Official customer media access verification

Vigilante SHALL require verification of Google's official API path, access
approval, OAuth scopes, account permissions, and quota state before implementing
customer-uploaded GBP photo retrieval.

#### Scenario: Developer starts GBP customer media work

- GIVEN the developer is assigned to solve customer-uploaded GBP photo access
- WHEN they begin the work
- THEN they first produce a technical recommendation based on current Google Business Profile API documentation and project access state

#### Scenario: Official access is confirmed

- GIVEN Google Business Profile APIs, OAuth scopes, location permissions, and quota are confirmed for customer media retrieval
- WHEN implementation begins
- THEN the solution uses the existing organization-level GBP connection and location binding model

#### Scenario: Official access remains blocked

- GIVEN Google approval, quota, or API limitations prevent customer media retrieval
- WHEN the product needs photo validation
- THEN the workflow keeps the blocked state visible and routes users to a labeled fallback process
