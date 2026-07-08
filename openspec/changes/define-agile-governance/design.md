## Context

`main` is protected and the repo now uses OpenSpec. The next risk is process
overcorrection: too much ceremony for tiny changes, or too little structure for
security-sensitive work.

## Approach

- Define five change levels from tiny to production/irreversible.
- Keep low-risk changes lightweight.
- Require OpenSpec, tests, and rollback notes only when behavior or risk justify it.
- Make the PR template reflect this risk-based model.

## Non-Goals

- No runtime changes.
- No additional GitHub protection rules.
- No requirement that every typo or docs tweak has a full OpenSpec proposal.
- No weakening of protected `main` checks.

## Verification

- Validate OpenSpec artifacts.
- Run `git diff --check`.
- Inspect PR template and governance doc for clear risk tiers.
