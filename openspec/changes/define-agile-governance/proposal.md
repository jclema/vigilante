## Why

The project needs governance that protects production, evidence, security, and
external developer collaboration without slowing down low-risk iteration.

## What Changes

- Add an agile governance playbook with risk-based change levels.
- Clarify when OpenSpec and `make check` are required versus optional.
- Update the PR template so contributors report relevant verification without
  pretending every docs-only change ran the full suite.
- Keep runtime behavior unchanged.

## Capabilities

### New Capabilities

- `development-governance`: Risk-based contribution process, PR gates, and merge expectations.

### Modified Capabilities

- None. This is process and documentation only.

## Impact

- Adds `docs/agile-governance.md`.
- Updates `.github/pull_request_template.md`.
- Adds OpenSpec artifacts for the governance decision.
- No application code, production dependency, schema, infrastructure, IAM, or secret changes.
