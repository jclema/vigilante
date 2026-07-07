- [x] Create the OpenSpec workspace and Codex command integration.
  - Verify: `npx --yes @fission-ai/openspec@latest status --change define-vigilante-product-operating-model --json`

- [x] Add portable Vigilante SDD rules, product context, agent definitions, and workflow skills.
  - Verify: `find ai-specs -type f | sort`

- [x] Seed baseline specs for product positioning, public scanning, evidence, case management, GBP integration, and operations.
  - Verify: `find openspec/specs -name spec.md | sort`

- [x] Connect agent-facing docs and OpenSpec config to the SDD layer.
  - Verify: `git diff --check`

- [x] Validate OpenSpec artifacts.
  - Verify: `npx --yes @fission-ai/openspec@latest validate --all --no-interactive`
