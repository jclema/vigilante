## Purpose

Defines a trustworthy command-center state so filters, paginated alerts, map markers, and selected-case details never communicate contradictory operational information.

## ADDED Requirements

### Requirement: Filtered alerts are authoritative
The command center SHALL derive its paginated alert rows, command-map markers, result count, and selected-case eligibility from the same active filters.

#### Scenario: Filters produce matching alerts
- **WHEN** an operator changes city, status, or priority filters and matching alerts exist
- **THEN** the alert page and command-map markers SHALL contain only alerts that satisfy those filters

#### Scenario: Pagination changes the visible alert page
- **WHEN** an operator moves to another page of filtered alerts
- **THEN** the command-map markers SHALL represent the alerts visible on that page

### Requirement: Selected case remains eligible and visible
The command center MUST display case details only for an alert that is visible on the current filtered page.

#### Scenario: Existing selection remains visible
- **WHEN** filters are applied and the selected alert remains visible on the current page
- **THEN** the selected case SHALL remain selected

#### Scenario: Existing selection leaves the visible page
- **WHEN** filters or pagination remove the selected alert from the visible page and another alert is visible
- **THEN** the first visible alert SHALL become selected in the list, map, and case inspector

### Requirement: Zero-result state clears stale operational context
The command center MUST clear alert selection when no alert is visible and MUST communicate the empty result consistently in the list, map, and case inspector.

#### Scenario: Filters produce zero alerts
- **WHEN** the active filters produce zero matching alerts
- **THEN** the list SHALL show an explicit empty state, the command map SHALL show zero markers, and the case inspector SHALL show no previous case data or case action

#### Scenario: Results return after an empty state
- **WHEN** an operator changes filters after a zero-result state and matching alerts become visible
- **THEN** the first visible alert SHALL become selected and its marker and case details SHALL be restored consistently

### Requirement: Static atlas limitations remain explicit
Until the command map is replaced with a geographic implementation, the command center MUST NOT present the Medellin atlas as the geographic representation of a selected city outside its supported metro-area context.

#### Scenario: Bogotá is selected
- **WHEN** the active city filter selects Bogotá D.C.
- **THEN** the map SHALL replace the Medellin atlas with a truthful contextual state for Bogotá and SHALL continue to report the matching alert count without fabricating marker positions

#### Scenario: All cities are selected
- **WHEN** the active city filter selects all cities
- **THEN** the map SHALL label the atlas as a temporary operational overview rather than an exact nationwide geographic view
