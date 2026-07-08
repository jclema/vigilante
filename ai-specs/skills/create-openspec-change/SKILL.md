---
name: create-openspec-change
description: Create a Vigilante OpenSpec change from a clear request using the repo's SDD standards.
---

# Create OpenSpec Change

Use when the user is ready to formalize a feature, fix, operational change, or
product decision.

## Steps

1. Read `openspec/config.yaml`, `ai-specs/docs/base-standards.md`, and
   `ai-specs/docs/product-context.md`.
2. Run `npx --yes @fission-ai/openspec@latest new change <kebab-name>`.
3. Create `proposal.md`, `design.md`, affected `specs/**/*.md`, and `tasks.md`.
4. Keep requirements behavior-level and scenarios testable.
5. Include verification commands in every task.
6. Validate with:

```bash
npx --yes @fission-ai/openspec@latest validate <kebab-name> --no-interactive
```
