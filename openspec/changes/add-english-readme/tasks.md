- [x] Add English README translation.
  - Verify: `test -f README.en.md`

- [x] Add language links to the Spanish and English README files.
  - Verify: `sed -n '1,6p' README.md README.en.md`

- [x] Validate documentation artifacts.
  - Verify: `npx --yes @fission-ai/openspec@latest validate --all --no-interactive && git diff --check`
