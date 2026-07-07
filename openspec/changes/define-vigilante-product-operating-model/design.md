## Context

OpenSpec should be adopted brownfield-first: specs grow from real changes instead
of attempting to convert the whole codebase at once. Vigilante already has a
useful README, operational docs, tests, and production runbook; the new layer
should point to those sources instead of duplicating them.

## Approach

- Use `openspec/config.yaml` to inject Vigilante stack, product, reliability, and
  security context into OpenSpec artifacts.
- Use `ai-specs/` as the portable Specboot-style source for agent rules, roles,
  and skills.
- Seed concise main specs for the product areas that already drive development.
- Keep the active change `define-vigilante-product-operating-model` as the audit
  trail for adopting SDD.
- Keep `AGENTS.md` short and reference the new SDD layer.

## Non-Goals

- No runtime behavior changes.
- No new Python or production dependency.
- No bulk migration of every README section into OpenSpec.
- No automatic reporting, enforcement, retention, schema, IAM, or Terraform change.

## Verification

- Validate OpenSpec artifacts with `npx --yes @fission-ai/openspec@latest validate --all --no-interactive`.
- Review links and generated files with `git diff --check`.
- Skip `make check` unless code changes are introduced.
