## Context

The developer speaks English and needs to understand the product, repo, current
progress, blockers, and contribution workflow. Current docs contain the needed
facts, but they are spread across README, AGENTS, ai-specs, OpenSpec specs, and
operational guides.

## Approach

- Create `docs/onboarding/developer-onboarding.md` as the primary entrypoint.
- Add `first-week-plan.md` for a low-risk ramp.
- Add `access-policy.md` to prevent premature access to cloud, secrets, and real evidence.
- Add `first-contribution-brief.md` to guide the first PR toward a safe, valuable slice.
- Reference existing canonical docs instead of duplicating every detail.

## Non-Goals

- No production access provisioning.
- No legal agreement drafting beyond technical access guidance.
- No app runtime changes.
- No migration of all docs to English.

## Verification

- Validate OpenSpec artifacts.
- Check markdown paths and links by inspection.
- Do not run `make check` unless runtime code changes are introduced.
