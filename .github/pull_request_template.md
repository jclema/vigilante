## Summary

<!-- What changed and why? Keep it short. -->

## Spec

<!-- Link the OpenSpec change or spec this PR implements. -->
<!-- For L0-L1 docs or tiny fixes, write "Not required: <reason>". -->

- OpenSpec change/spec:

## Verification

<!-- List exact commands run. -->
<!-- Use the checks that match the risk level. Do not claim commands you did not run. -->

- [ ] `npx --yes @fission-ai/openspec@latest validate --all --no-interactive`
- [ ] `make test`
- [ ] `make check` for code changes with behavior, security, persistence, or production risk
- [ ] `make smoke` if routes, auth, templates, login, or production boot behavior changed

## Risk Check

- [ ] No credentials, `.env`, service accounts, browser storage state, or customer evidence included
- [ ] Organization-level authorization preserved
- [ ] Evidence provenance preserved
- [ ] Human review preserved before external reporting or enforcement
- [ ] No production infrastructure, IAM, secrets, retention, or destructive cleanup changes without explicit approval

Risk level:

- [ ] L0 tiny
- [ ] L1 low risk
- [ ] L2 product behavior
- [ ] L3 sensitive behavior
- [ ] L4 production or irreversible

## Screenshots

<!-- Include screenshots for UI changes. -->
