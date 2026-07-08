# Documentation Standards

## Canonical Docs

- `README.md`: current pilot scope, setup, commands, product state.
- `AGENTS.md`: short agent entrypoint and repo map.
- `docs/watchmanhub-production-runbook.md`: production operations.
- `docs/google-cloud-pilot.md`: deployment checklist.
- `docs/experimental-browser-capture.md`: limits for browser capture.
- `docs/gbp-access-matrix-guide.md`: GBP onboarding and access data.
- `openspec/`: living specs and change artifacts.
- `ai-specs/`: reusable agent rules, roles, and skills.

## Rules

- Do not duplicate long product narratives across docs. Link to canonical files.
- Update docs when changing configuration, deployment, public workflows,
  environment variables, external service behavior, or operational response.
- Specs describe behavior. Designs describe implementation. Runbooks describe
  operating commands and rollback.
- Keep docs concise enough for agents to load into context without drowning the
  implementation task.
