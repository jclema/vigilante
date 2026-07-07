## Context

The repository now has English onboarding docs, but GitHub still opens the
Spanish README by default. Keeping the Spanish README as default preserves the
current project language while an English version gives external contributors a
complete starting point.

## Approach

- Create `README.en.md` as a faithful English version of the current README.
- Add a compact language selector immediately after the title in both files.
- Do not translate or rename existing Spanish operational docs in this change.
- Do not modify app behavior.

## Non-Goals

- No runtime changes.
- No full translation of every doc.
- No changes to production operations or setup commands.

## Verification

- Validate OpenSpec artifacts.
- Run `git diff --check`.
- Inspect README links and rendered markdown structure.
