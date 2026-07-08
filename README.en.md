# Vigilante

[English](README.en.md) | [Español](README.md)

Vigilante is a pilot for detecting impersonation of Yamaha dealers on Google
Maps, consolidating evidence, and helping a human decide whether a case should
be escalated, archived, or reported.

It is not an autonomous enforcement system. Today it is an assisted operations
product focused on:

- public detection of cloned or suspicious locations
- evidence analysis and case dossier creation
- operational management by network, dealer, and branch
- report preparation with human approval

## Production

The public application is available at:

- [https://www.watchmanhub.com](https://www.watchmanhub.com)

The public production request path is:

```text
Cloudflare
  -> Google Cloud Global External Application Load Balancer
  -> Cloud Armor
  -> Serverless NEG
  -> Cloud Run
  -> Firestore and Cloud Storage
```

Active controls:

- Managed TLS for `watchmanhub.com` and `www.watchmanhub.com`
- HTTP to HTTPS redirect and canonical `www` domain
- Cloud Run restricted to internal and Load Balancer traffic
- Public `run.app` URL blocked from direct internet access
- Cloud Armor connected with managed rules in preview
- Separate service accounts for runtime and Cloud Scheduler
- Scheduler authenticated with OIDC
- Secrets managed with Secret Manager
- Secure cookies and defensive HTTP headers
- Demo data disabled in production

## Real Project State

The product has moved from a generic prototype into an operational pilot with
UI, cases, dossier, territory map, network hierarchy, and integration routes.
The important current state is:

- public monitoring of cloned locations works
- case management, dossier, and manual operations work
- the new organizational structure is modeled
- the formal Google Business Profile integration is implemented in software
- real access to GBP `customer media` was not enabled by Google
- automated browser capture against Google Maps is not reliable in Cloud Run

In short: Vigilante can already operate the pilot and validate real human
workflows, but it still does not have a stable official source for GBP photos.

## Executive Summary

### What We Achieved

1. Built a usable operations dashboard.
2. Rebuilt the login, dashboard, case detail, and settings UX.
3. Simplified cards, copy, and visual hierarchy so the system feels lighter.
4. Modeled the correct network hierarchy:
   - Vigilante platform
   - Global network view
   - Yamaha Official Network
   - Dealers
   - Branches
5. Adjusted whitelist, organizations, and real branches for the Yamaha network.
6. Fixed the logic so cases and alerts aggregate to the right organization.
7. Repaired the public scan endpoint so it accepts trusted Cloud Scheduler traffic.
8. Left the formal GBP `customer media` route operational in software, with clear UI blockers.
9. Reinserted visual evidence into the dossier for manipulated-photo cases.
10. Documented that browser capture is experimental and must not be treated as official evidence.

### What Did Not Work

1. Google repeatedly blocked or degraded automated browser capture.
2. The project did not receive Google approval for real GBP API access with operational quota.
3. Without approval, Business Information API `Requests per minute` stayed at `0`.
4. Without approved quota, we cannot read official `customer media` even though the technical integration is ready.

### Why It Did Not Work

This was not primarily a code problem. The blocker was external in two layers:

1. Google Maps detects and limits automated traffic, including redirects to `google.com/sorry`.
2. Google rejected the GBP access request because the account or project did not pass its internal quality checks.

## Product Context

The problem Vigilante solves is operational, not only technical.

Official dealers can be affected by:

- cloned profiles
- fake branches
- manipulated photos
- phishing inside Google Maps

The manual work required to detect, compare, document, and follow up on these
incidents consumes time, spreads across people, and leaves limited traceability.
Vigilante exists to centralize:

- monitoring
- evidence
- scoring
- human decision-making
- follow-up

## Product Development Process

This is the real path the pilot has followed.

### Phase 1. System Base

The FastAPI app was built with:

- authentication
- organizations and roles
- server-rendered dashboard
- cases, evidence, and timeline
- Scout, Forensic, and Reporter services

### Phase 2. Operations and UX

The UI and UX were deeply revised to make the app more direct:

- clearer, more modern login
- dashboard with more operational maps and cards
- more readable dossiers
- settings organized by active view
- less narrative, more actionable messages

### Phase 3. Real Network Hierarchy

The operational architecture was rebuilt around:

- one Yamaha Official Network
- several dealers within that network
- one or more branches per dealer

This required:

- migrating case and alert associations
- rebuilding dropdowns and active views
- updating whitelist and real dealers
- fixing aggregations for protected profiles, alerts, and command views

### Phase 4. Public Detection

The public scan for possible clones and suspicious profiles was stabilized.

The `/api/scans/run` endpoint was also fixed so it accepts trusted Cloud
Scheduler executions with the real headers it sends.

This made the most important part of the current pilot functional: public
scanning and case creation.

### Phase 5. Photos and Evidence

We tried two paths in parallel.

#### Path A. Public Browser Capture

An experimental Playwright flow was built to:

- open official profiles
- navigate to photos
- take screenshots
- ingest evidence

It was improved with:

- `storage_state`
- local Chrome and CDP variants
- profile filters
- landing validation

Result:

- it remains experimental
- in Cloud Run, Google blocks it or sends it to the wrong landing page
- it cannot be treated as a stable source

#### Path B. Formal GBP Integration

The formal route for reading official `customer media` was implemented:

- organization-level OAuth
- GBP account connection
- location binding
- manual backfill from settings
- clear status and blocker messages

Result:

- the technical integration is ready
- the platform shows the blocker correctly
- Google did not enable real access

## What Works Today

| Capability | Status | Comment |
|---|---|---|
| Login, roles, and sessions | Functional | Google OAuth in production; demo only local |
| Operations dashboard | Functional | Platform, network, and dealer views |
| Territory map | Functional | Operational focus on alerts |
| Case management | Functional | Triage, dossier, timeline, and operations |
| Public clone detection | Functional | Most reliable product route today |
| Manipulated-photo dossier | Functional | Visual evidence restored |
| Network -> dealer -> branch hierarchy | Functional | Adjusted to the real Yamaha structure |
| Guided browser enforcement | Functional with limits | Human-in-the-loop |
| Formal GBP ingest in code | Functional in software | Externally blocked by Google |
| Public photo capture with Playwright | Experimental | Not reliable in Cloud Run |

Public authentication uses `https://www.watchmanhub.com/auth/google/callback`.
Demo accounts only belong to the local environment, and their known credentials
are rejected in production.

## What Does Not Work Today

| Topic | Status | Reason |
|---|---|---|
| Official GBP customer media | Blocked | Google rejected project access |
| Operational Business Information API quota | Blocked | `Requests per minute = 0` |
| Browser photo scraper in cloud | Unstable | Antibot and redirect to `google.com/sorry` |
| Automated official-photo coverage | Unavailable | Depends on one of the two points above |

## Where We Are Now

Vigilante is in a healthy intermediate state:

- the product has a real operational shape
- the case flow is usable
- the network and dealers are modeled
- public monitoring already creates value
- the main pending blocker is the official or reliable GBP photo source

We are not blocked from improving the product. We are blocked from validating
the official photos module as a real production capability.

## What Must Be Solved

### P0. Solve the Official Photo Source

There are two paths:

1. Reapply correctly to GBP API and secure real Google approval.
2. Define a human or semi-automated fallback for photos while approval is pending.

My current read is clear: this is the main bottleneck.

### P0. Confirm Operational Reporting Criteria

We have moved toward a model where the system prepares and the human decides.
The remaining criteria to close are:

- real high-certainty threshold
- minimum evidence required for a report
- how to document evidence and later follow-up
- when a case is archived as a false positive

### P0. Measure Precision with Real Cases

We need a dataset and operating routine to measure:

- alert precision
- false positives
- triage time
- time to decision
- real value per dealer

### P1. Production Operations

Firestore, Cloud Storage, Secret Manager, Load Balancer, and separate identities
are already operational. Remaining work:

- evidence retention
- alerts and observability dashboards
- audit trail
- runbooks
- recovery from external failures
- calibration and final enforcement of Cloud Armor

## Current Recommended Plan

### Workstream 1. Product

Keep improving what already creates value without depending on Google:

1. operations dashboard
2. case detail
3. dealer command view
4. filters, history, and traceability
5. evidence and manual follow-up

### Workstream 2. Official GBP

Do not keep investing hours in technical hacks until approval is solved.

The right path now is:

1. fix what is needed in the website, business, and profile to meet Google's criteria
2. reapply
3. wait for real quota approval
4. reconnect and retest `customer media`

### Workstream 3. Operational Fallback

If the business needs photo validation before approval, define a controlled
manual or semi-assisted workflow instead of continuing to bet on fragile cloud
scraping.

## Demo Credentials

Base demo accounts live in `app/services/demo_data.py`.
They are only loaded locally when `SEED_DEMO_DATA=true`. Production requires
`SEED_DEMO_DATA=false` and rejects insecure startup configurations.

- `operator@vigilante.local` / `change-me`
- `yamaha@vigilante.local` / `yamaha-demo`
- `bello@motoblu.local` / `dealer-demo`
- `asesor.bello@motoblu.local` / `dealer-demo`

## Quick Start

Requirements:

- Python 3.11 or higher
- `make`
- `curl` for smoke tests
- Docker only if validating containers

```bash
git clone <repository-url>
cd vigilante
make setup
make run
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Canonical Commands

```bash
make setup       # create .venv and install app + development tools
make run         # start local FastAPI app
make test        # run tests
make lint        # run Ruff
make format      # format Python files
make build       # build wheel and source distribution
make smoke       # verify /login responds
make check       # lint, tests, package build, and compile checks
```

## Repository Architecture

```text
app/
  agents/        Scout, Forensic, and Reporter
  services/      authentication, integrations, evidence, and operations
  templates/     server-rendered dashboard
  static/        styles and assets
  main.py        FastAPI routes and wiring
  models.py      domain model
  store.py       in-memory and Firestore repositories
docs/            operational guides, matrices, and plans
infra/           Terraform and infrastructure
scripts/         reusable operational tools
tests/           unit and API tests
```

## Configuration

```bash
cp .env.example .env
```

Minimum variables for demo:

```dotenv
APP_ENV=development
STORAGE_BACKEND=memory
SEED_DEMO_DATA=true
SESSION_SECRET=<random-local-value>
```

Important external integrations:

- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_GBP_WEBHOOK_SECRET`
- `GOOGLE_CLOUD_PROJECT`
- `EVIDENCE_BUCKET_NAME`
- `ALERT_WEBHOOK_URL`
- SMTP if applicable

Never commit credentials, service accounts, real evidence, or browser
`storage_state` to Git.

## Key Documentation

- [`AGENTS.md`](AGENTS.md): quick repo map for agents.
- [`openspec/specs`](openspec/specs): living product and behavior specs.
- [`openspec/changes`](openspec/changes): active and archived Spec-Driven Development changes.
- [`ai-specs/docs/base-standards.md`](ai-specs/docs/base-standards.md): portable rules for agents.
- [`ai-specs/docs/product-context.md`](ai-specs/docs/product-context.md): product context, users, and opportunity.
- [`docs/onboarding/developer-onboarding.md`](docs/onboarding/developer-onboarding.md): English onboarding for external developers.
- [`docs/google-cloud-pilot.md`](docs/google-cloud-pilot.md): pilot deployment checklist.
- [`docs/watchmanhub-production-runbook.md`](docs/watchmanhub-production-runbook.md): production operation, diagnostics, and rollback.
- [`docs/gbp-access-matrix-guide.md`](docs/gbp-access-matrix-guide.md): GBP access intake.
- [`docs/experimental-browser-capture.md`](docs/experimental-browser-capture.md): limits and usage for the experimental scraper.
- [`Agente IA Anti-Phishing Google Maps.md`](Agente%20IA%20Anti-Phishing%20Google%20Maps.md): original research and proposal.

## Spec-Driven Development

Vigilante uses OpenSpec as its living specification layer. For non-trivial
product, behavior, integration, security, operations, or architecture changes:

```bash
/opsx:explore
/opsx:propose <change-name>
/opsx:apply <change-name>
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
/opsx:archive <change-name>
```

Practical rule: if the change affects cases, evidence, scoring, permissions,
reports, GBP, Places, production operations, or the main product experience, it
must first be expressed as a spec with acceptance criteria and scenarios.

## Delivery Rule

Before closing changes:

```bash
make check
make smoke
```

If a change touches scoring, authorization, persistence, retention, or external
actions, it must include:

- tests
- acceptance criteria
- clear rollback
