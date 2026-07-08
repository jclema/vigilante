# First Contribution Brief

Use this brief to give the external developer a safe first task.

## Recommended Task

Improve confidence around organization-scoped case visibility.

## Why This Task

Organization-level authorization is core to Vigilante. A developer who can read
the existing case workflow, understand the user scope, and add a focused test or
small improvement has learned the right part of the system without requiring
production access.

## Scope

Allowed:

- Read existing dashboard and API tests.
- Add or refine tests for case visibility by organization.
- Improve small docs around the tested behavior if useful.
- Use an OpenSpec change to capture the behavior being protected.

Not allowed:

- Schema changes.
- Production auth changes.
- Google OAuth changes.
- Cloud infrastructure changes.
- Broad dashboard redesign.

## Suggested Files to Inspect

- `tests/test_dashboard.py`
- `tests/test_production_security.py`
- `app/main.py`
- `app/services/dashboard.py`
- `app/services/organization_resolution.py`
- `app/models.py`
- `app/store.py`
- `openspec/specs/case-management/spec.md`

## Acceptance Criteria

- The developer can explain which organization should see which cases.
- At least one focused test protects the expected visibility behavior or an
  existing test is clarified without weakening coverage.
- The change passes:

```bash
make test
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

- If code changes are included, the final PR also passes:

```bash
make check
```

## Review Questions

- Did the change preserve organization-level authorization?
- Did the developer avoid production access and secrets?
- Did the PR link to the relevant spec?
- Is the change small enough to review quickly?
- Did tests prove behavior instead of only testing implementation details?
