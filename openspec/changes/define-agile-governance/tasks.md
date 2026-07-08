- [x] Add agile governance playbook.
  - Verify: `test -f docs/agile-governance.md`

- [x] Update PR template for risk-based verification.
  - Verify: `sed -n '1,220p' .github/pull_request_template.md`

- [x] Validate documentation artifacts.
  - Verify: `npx --yes @fission-ai/openspec@latest validate --all --no-interactive && git diff --check`
