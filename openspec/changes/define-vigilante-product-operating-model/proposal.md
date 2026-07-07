## Why

Vigilante is moving from pilot implementation into a product that must scale
across more markets, users, and fraud workflows. Requirements currently live
across README, runbooks, code, tests, and chat context; OpenSpec gives the
project a living spec layer before code changes.

## What Changes

- Add a repo-local OpenSpec workspace for change proposals, specs, designs, and
  tasks.
- Add a portable `ai-specs/` layer with Vigilante-specific development rules,
  product context, agent definitions, and workflow skills inspired by Specboot.
- Seed the first behavior specs for product positioning, public scanning,
  evidence, case management, GBP integration, and operations.
- Keep existing runtime behavior unchanged.

## Capabilities

### New Capabilities

- `product-positioning`: Market, user, and operating model requirements.
- `public-scanning`: Public Places scanning behavior and limits.
- `evidence`: Evidence provenance and reliability requirements.
- `case-management`: Human-reviewed case workflow behavior.
- `gbp-integration`: GBP connection, customer media, and blocked-access fallback behavior.
- `operations`: Production operations and deployment safety behavior.

### Modified Capabilities

- None. This is the first OpenSpec baseline and does not change application runtime behavior.

## Impact

- Adds `openspec/`, `.codex/`, and `ai-specs/` documentation and workflow artifacts.
- Updates agent-facing repo guidance to reference the SDD layer.
- No production dependencies, APIs, schemas, infrastructure, or runtime code change.
