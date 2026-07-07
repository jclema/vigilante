# Vigilante SDD Base Standards

This is the portable source of truth for AI-assisted development in Vigilante.
OpenSpec owns change artifacts. This folder owns reusable rules, agent roles, and
workflow skills.

## Core Principles

- Start with product intent, users, constraints, acceptance criteria, risks, and success metrics before implementation.
- Use OpenSpec for any feature, behavior change, architecture change, production operation, or ambiguous request.
- Keep changes as small vertical slices that can be tested end-to-end.
- Preserve explicit human review before irreversible reports, external enforcement, or destructive cleanup.
- Validate external data at service boundaries and keep evidence provenance visible.
- Prefer simple, production-ready changes over clever abstractions.
- Update specs first when scope, behavior, data contracts, or operational assumptions change.

## Language

- Product and internal planning docs may be Spanish or English.
- Code, identifiers, logs, env vars, API paths, test names, and structured technical contracts should stay in English.
- User-facing Spanish copy is acceptable where it matches the existing product.

## Canonical Commands

Run from repo root:

```bash
make setup
make run
make test
make lint
make build
make smoke
make check
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

## Boundaries

Always:

- Read relevant OpenSpec artifacts before changing behavior.
- Add or update tests for behavior changes.
- Keep demo and production behavior distinguishable.
- Preserve organization-level authorization and evidence provenance.
- Treat Google APIs, Maps pages, browser automation, webhooks, and notifications as unreliable.

Ask first:

- Adding a production dependency.
- Changing persistence schemas, retention, IAM, Terraform, secrets, or destructive cleanup behavior.
- Enabling automatic external reporting or enforcement.
- Weakening security controls, production checks, or failing tests.

Never:

- Commit credentials, browser storage state, customer evidence, service accounts, or `.env`.
- Treat experimental browser capture as authoritative GBP evidence.
- Remove or weaken a failing test just to make checks pass.

## OpenSpec Workflow

- Use `/opsx:explore` for vague ideas, market opportunities, and unclear product intent.
- Use `/opsx:propose <change-name>` for scoped feature or behavior changes.
- Use `/opsx:apply <change-name>` only after proposal, specs, design, and tasks are coherent.
- Use `/opsx:verify` or `npx --yes @fission-ai/openspec@latest validate --all --no-interactive` before handoff.
- Use `/opsx:archive <change-name>` after the implementation is verified and specs are synced.
