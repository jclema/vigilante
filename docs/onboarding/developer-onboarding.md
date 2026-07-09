# External Developer Onboarding

This guide is for a new English-speaking developer joining Vigilante /
WatchmanHub. Read it before writing code.

## Product Summary

Vigilante is an operations product for detecting impersonation and fraud risks
around authorized business locations on Google Maps, Google Business Profile
and Google Places. The current public product is WatchmanHub:

- Production URL: `https://www.watchmanhub.com`
- Current pilot focus: Yamaha dealer monitoring
- Product type: human-reviewed operations dashboard, not autonomous enforcement

The product helps operators detect suspicious public listings, assemble
evidence, score risk, manage cases, and decide what should be escalated,
archived, or reported.

## What Works Today

- Login, roles, sessions, and organization-scoped views.
- Server-rendered operations dashboard.
- Case management, case detail, evidence, timeline, and triage workflows.
- Organization hierarchy for platform, network, dealer, and branch contexts.
- Public scan flow for suspicious Google Places results.
- Google Business Profile connection flow implemented in software.
- Production deployment on Google Cloud behind Cloudflare, Load Balancer,
  Cloud Armor, Cloud Run, Firestore, Cloud Storage, Secret Manager, and
  Cloud Scheduler.

## Known Constraints

- Official GBP customer media access is blocked externally by Google approval
  and quota. The code path exists, but production access is not currently
  usable.
- Public Google Maps browser automation is experimental and unreliable in cloud
  environments.
- Browser capture must never be treated as authoritative GBP evidence.
- The product must preserve human review before irreversible reports or
  enforcement actions.
- Production secrets, real customer evidence, browser storage state, service
  accounts, and `.env` files must never be committed.

## Required Reading Order

1. `README.md`
2. `AGENTS.md`
3. `ai-specs/docs/product-context.md`
4. `ai-specs/docs/base-standards.md`
5. `docs/onboarding/gbp-customer-media-one-pager.md`
6. `docs/plans/active/gbp-customer-media-access.md`
7. `openspec/changes/define-gbp-customer-media-access/proposal.md`
8. `openspec/specs/product-positioning/spec.md`
9. `openspec/specs/case-management/spec.md`
10. `openspec/specs/evidence/spec.md`
11. `openspec/specs/public-scanning/spec.md`
12. `openspec/specs/gbp-integration/spec.md`
13. `openspec/specs/operations/spec.md`
14. `docs/watchmanhub-production-runbook.md`
15. `docs/experimental-browser-capture.md`
16. `docs/gbp-access-matrix-guide.md`

## Local Setup

Requirements:

- Python 3.11+
- Node.js 20.19.0+ for OpenSpec via `npx`
- `make`
- `curl`

Commands:

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

Local demo environment:

```bash
cp .env.example .env
```

Use local demo settings only. Do not request production secrets for first-week
work unless explicitly approved.

## Development Workflow

Use Spec-Driven Development for any non-trivial change:

```bash
/opsx:explore
/opsx:propose <change-name>
/opsx:apply <change-name>
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
make check
/opsx:archive <change-name>
```

Every pull request should identify:

- The OpenSpec change or spec it implements.
- The user workflow affected.
- Tests and verification commands run.
- Any production, security, data, or external-service risk.

## Architecture Map

- `app/main.py`: FastAPI routes and application wiring.
- `app/agents/`: Scout, Forensic, and Reporter domain agents.
- `app/services/`: auth, integrations, evidence, dashboard, operations, and notifications.
- `app/models.py`: domain models and enums.
- `app/store.py`: in-memory and Firestore repository behavior.
- `app/templates/`: server-rendered Jinja views.
- `app/static/`: static CSS and image assets.
- `tests/`: unit and API-level tests.
- `scripts/`: reusable operational commands.
- `infra/terraform/`: Google Cloud infrastructure.
- `docs/`: operational and onboarding docs.
- `openspec/`: living specs and change artifacts.
- `ai-specs/`: reusable rules, agents, and skills for AI-assisted development.

## Contribution Rules

Always:

- Read the relevant specs, tests, and docs before changing behavior.
- Keep changes small and testable.
- Add or update tests for behavior changes.
- Preserve organization-level authorization.
- Preserve evidence provenance.
- Keep demo and production behavior separate.

Ask before:

- Adding dependencies.
- Changing persistence schemas, retention, IAM, Terraform, secrets, or cleanup behavior.
- Touching production infrastructure.
- Enabling automatic reporting or enforcement.
- Weakening production checks or security controls.

Never:

- Commit credentials or customer evidence.
- Treat browser capture as official GBP evidence.
- Remove or weaken a failing test just to pass CI.
- Make production changes without explicit approval.

## Best First Contributions

Good first tasks are small vertical slices:

- Add or improve tests around existing case visibility or evidence behavior.
- Improve one case detail or dashboard workflow with existing data.
- Convert an existing product decision into an OpenSpec change.
- Improve docs where current behavior is already implemented.
- Add operational checks that do not require production access.

Avoid first:

- Google Cloud IAM, Terraform, or Secret Manager changes.
- Production OAuth or GBP approval work.
- Data retention or destructive cleanup.
- Automated external reporting or enforcement.
- Large visual redesigns.
