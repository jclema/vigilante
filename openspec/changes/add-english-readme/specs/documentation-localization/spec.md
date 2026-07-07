## ADDED Requirements

### Requirement: Bilingual README discovery

Vigilante SHALL expose both Spanish and English README versions from the top of
each README file.

#### Scenario: English-speaking developer opens the Spanish README

- GIVEN a developer opens `README.md`
- WHEN they inspect the top of the document
- THEN they can navigate to `README.en.md`

#### Scenario: Spanish-speaking developer opens the English README

- GIVEN a developer opens `README.en.md`
- WHEN they inspect the top of the document
- THEN they can navigate to `README.md`

### Requirement: English project overview

Vigilante SHALL provide an English README that explains product scope, current
state, setup, architecture, key docs, and SDD workflow.

#### Scenario: External developer starts from GitHub

- GIVEN an English-speaking developer opens `README.en.md`
- WHEN they read the document
- THEN they can understand the current product state, known blockers, local setup, and contribution workflow
