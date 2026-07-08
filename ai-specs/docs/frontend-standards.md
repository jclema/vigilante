# Frontend Standards

Vigilante uses server-rendered Jinja templates and static assets, not a SPA.

## Stack

- Templates: `app/templates/`
- Static CSS/images: `app/static/`
- Routing and template wiring: `app/main.py`

## Rules

- Preserve the operational dashboard focus: dense, scannable, and action-ready.
- Avoid marketing-style layouts inside the app.
- Keep labels short and outcome-focused.
- Ensure dashboard, case detail, and settings views remain usable across platform,
  network, dealer, and branch contexts.
- Do not hide uncertainty. Evidence limitations and Google access blockers must
  be visible where they affect decisions.

## Verification

- Add API or template-render tests for user-facing behavior changes.
- Use `make smoke` when routing, sessions, login, or template boot behavior
  changes.
