# Codex harness v1

## Objective

Make Vigilante installable, runnable, and verifiable by a fresh Codex session
without reconstructing project commands or conventions.

## Scope

- Add a short root `AGENTS.md` as the repository map.
- Define canonical setup, run, test, lint, build, smoke, and check commands.
- Make `pyproject.toml` the package and dependency source of truth.
- Make CI execute the same checks used locally.
- Preserve existing application behavior.

## Acceptance criteria

- `make setup` succeeds from a clean Python 3.11+ environment.
- `make check` passes.
- `make smoke` boots the app and reaches `/login`.
- The Python package contains templates and static assets.
- Both Docker images build in CI.
- A new agent can find project boundaries and commands from `AGENTS.md`.

## Risks

- Existing lint findings may reveal real runtime defects.
- Packaging changes can omit non-Python UI assets unless explicitly configured.
- Browser capture remains dependent on Playwright and external Google behavior.

## Rollout

1. Land the repository contract and commands.
2. Verify locally in a clean virtual environment.
3. Run CI including package and container builds.
4. Follow with architecture, acceptance-criteria, and operations documentation.

