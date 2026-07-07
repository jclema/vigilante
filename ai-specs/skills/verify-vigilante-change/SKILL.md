---
name: verify-vigilante-change
description: Verify a Vigilante change against OpenSpec artifacts, tests, docs, and operational risks.
---

# Verify Vigilante Change

Use before handoff or archive.

## Steps

1. Run OpenSpec validation:

```bash
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

2. For code changes, run the narrowest relevant tests first, then `make check`.
3. For route, auth, login, production boot, or template changes, run `make smoke`.
4. Confirm docs or `.env.example` were updated for config, deployment, or
   operational changes.
5. Check that new behavior preserves organization scope, evidence provenance,
   and human approval for external actions.
6. Report remaining risks and any commands that could not be run.
