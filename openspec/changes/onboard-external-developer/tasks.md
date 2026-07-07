- [x] Add English external developer onboarding docs.
  - Verify: `find docs/onboarding -type f | sort`

- [x] Add OpenSpec artifacts for the onboarding process.
  - Verify: `npx --yes @fission-ai/openspec@latest status --change onboard-external-developer --json`

- [x] Validate OpenSpec artifacts.
  - Verify: `npx --yes @fission-ai/openspec@latest validate --all --no-interactive`
