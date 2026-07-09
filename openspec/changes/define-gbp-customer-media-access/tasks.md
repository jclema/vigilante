- [x] Create the developer-facing GBP customer media work brief.
  - Verify: `test -f docs/plans/active/gbp-customer-media-access.md`

- [x] Add OpenSpec requirements for official GBP customer media access research and fallback behavior.
  - Verify: `test -f openspec/changes/define-gbp-customer-media-access/specs/gbp-integration/spec.md`

- [x] Add OpenSpec requirements for GBP media evidence provenance.
  - Verify: `test -f openspec/changes/define-gbp-customer-media-access/specs/evidence/spec.md`

- [x] Validate OpenSpec artifacts.
  - Verify: `npx --yes @fission-ai/openspec@latest validate --all --no-interactive && git diff --check`
