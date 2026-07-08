# Agile Governance Playbook

Vigilante should move fast without becoming careless. The rule is simple:
increase ceremony only when risk increases.

## Operating Principle

Default to small, spec-backed vertical slices. Keep the path lightweight for
documentation, tests, and low-risk UI changes. Add stricter review for security,
evidence, production, persistence, authorization, and external actions.

## Change Levels

| Level | Examples | Required Process |
|---|---|---|
| L0: Tiny | typo, link, comment, copy-only clarification | direct small PR, no OpenSpec required |
| L1: Low risk | docs, onboarding, tests that do not change behavior, small UI copy | short PR, OpenSpec optional unless product meaning changes |
| L2: Product behavior | case workflow, dashboard behavior, evidence display, scoring copy, GBP state UX | OpenSpec change, focused tests, PR review |
| L3: Sensitive behavior | authorization, evidence provenance, reporting, persistence, retention, security controls | OpenSpec change, tests, `make check`, explicit risk notes |
| L4: Production or irreversible | IAM, Terraform, secrets, destructive cleanup, external reporting or enforcement | explicit approval, rollback plan, runbook update, staged rollout |

## Default Workflow

For L0-L1:

```bash
git checkout main
git pull origin main
git checkout -b codex/<small-change>
```

Open a PR with a short summary and the verification actually run.

For L2-L4:

```bash
/opsx:explore
/opsx:propose <change-name>
/opsx:apply <change-name>
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

Then run the relevant tests. Use `make check` before merge for code changes
with meaningful behavior or production risk.

## Required Gates

Always required:

- Pull request into `main`
- CI checks passing
- No secrets, `.env`, customer evidence, service accounts, or browser storage state
- Review before merge

Required for L2-L4:

- OpenSpec change or updated spec
- Clear acceptance criteria
- Focused tests or explicit manual verification
- Risk notes in the PR

Required for L3-L4:

- `make check`
- rollback or recovery note
- docs or runbook update when operations/config changes

## What Not To Do

- Do not write a full spec for a typo.
- Do not bypass specs for behavior that affects cases, evidence, permissions,
  production, or external actions.
- Do not add process that nobody will use.
- Do not hide uncertainty around Google APIs, GBP access, browser automation, or
  evidence reliability.

## Merge Policy

`main` is protected and represents the approved state of the product. Work
happens in short-lived branches. PRs should be small enough to review quickly.

Good branch names:

```text
codex/evidence-fallback-v1
developer/org-scope-tests
fix/gbp-status-copy
docs/update-onboarding
```

The best PR is boring: small scope, clear spec or rationale, passing checks, and
no surprise risk.
