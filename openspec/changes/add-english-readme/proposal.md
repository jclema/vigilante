## Why

An English-speaking external developer needs a clear entrypoint into the repo.
The current README is Spanish-only, so GitHub visitors and contributors who do
not speak Spanish cannot understand scope, status, setup, risks, and workflow
from the default project documentation.

## What Changes

- Add an English README translation as `README.en.md`.
- Add language links at the top of both README files.
- Keep `README.md` as the Spanish default.
- Keep runtime behavior unchanged.

## Capabilities

### New Capabilities

- `documentation-localization`: Bilingual README discovery and contributor onboarding documentation.

### Modified Capabilities

- None. This is documentation-only.

## Impact

- Adds `README.en.md`.
- Updates the first lines of `README.md`.
- No application code, production dependency, schema, infrastructure, or secret changes.
