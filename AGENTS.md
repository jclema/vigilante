# Vigilante agent map

This file is the entry point for coding agents. Keep it short and point to the
repository sources of truth instead of duplicating them here.

## Product

Vigilante is a FastAPI pilot for detecting impersonation of authorized Yamaha
dealers on Google Maps. It combines public Places scans, Google Business Profile
events, evidence analysis, case management, notifications, and a server-rendered
operations dashboard.

## Repository map

- `app/main.py`: FastAPI routes and application wiring.
- `app/agents/`: Scout, Forensic, and Reporter domain agents.
- `app/services/`: integrations and application services.
- `app/models.py`: domain models and enums.
- `app/store.py`: in-memory and Firestore repository behavior.
- `app/templates/`, `app/static/`: server-rendered UI.
- `tests/`: unit and API-level tests.
- `scripts/`: reusable operational commands.
- `infra/terraform/`: Google Cloud infrastructure.
- `docs/`: operational guides and project knowledge.
- `docs/plans/active/`: approved work that is not finished.
- `openspec/`: living specs and change artifacts for spec-driven development.
- `ai-specs/`: portable rules, agent definitions, and workflow skills.

## Canonical commands

Run commands from the repository root.

```bash
make setup       # create .venv and install app + development tools
make run         # start local app with demo data
make test        # run the test suite
make lint        # run static checks
make format      # format Python files
make build       # build wheel and source distribution
make smoke       # boot the app and probe the login page
make check       # lint, tests, package build, and compile checks
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

## Spec-driven workflow

- Use `openspec/` for non-trivial product, behavior, architecture, operations,
  security, or integration changes.
- Start vague opportunities with `/opsx:explore`.
- Start scoped changes with `/opsx:propose <change-name>`.
- Implement only after proposal, specs, design, and tasks are coherent.
- Read `ai-specs/docs/base-standards.md` and `ai-specs/docs/product-context.md`
  before creating or applying OpenSpec changes.

## Working agreements

- Read the relevant tests and docs before changing behavior.
- Read relevant OpenSpec artifacts before implementing non-trivial behavior.
- Implement small vertical slices and keep tests green.
- Add or update tests for behavior changes.
- Treat external Google APIs and browser automation as unreliable boundaries.
- Preserve explicit human review before irreversible reports or enforcement.
- Update `.env.example` and operational docs when configuration changes.
- Use repository-relative links in documentation.

## Boundaries

Always:

- Validate external data at service boundaries.
- Keep demo and production behavior distinguishable.
- Preserve organization-level authorization and evidence provenance.
- Run `make check` before handing work back.

Ask first:

- Adding a production dependency.
- Changing persistence schemas, retention, or destructive cleanup behavior.
- Enabling automatic external reporting or enforcement.
- Changing Google Cloud resources, IAM, or secrets.

Never:

- Commit credentials, browser storage state, customer evidence, or `.env`.
- Treat experimental browser capture as authoritative GBP evidence.
- Remove or weaken a failing test only to make checks pass.

## Current operational references

- `README.md`: local setup and current pilot scope.
- `openspec/specs/`: living product and behavior specs.
- `ai-specs/docs/base-standards.md`: portable SDD rules for agents.
- `ai-specs/docs/product-context.md`: product strategy and operating context.
- `docs/agile-governance.md`: risk-based workflow for moving fast with guardrails.
- `docs/google-cloud-pilot.md`: deployment checklist.
- `docs/experimental-browser-capture.md`: experimental capture limitations.
- `docs/gbp-access-matrix-guide.md`: GBP onboarding data.
- `Agente IA Anti-Phishing Google Maps.md`: original product and threat model.
