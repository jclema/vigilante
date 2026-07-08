# First Week Plan

This plan assumes the developer has GitHub access but no production cloud,
secret, or customer-evidence access.

## Day 1: Product and Repo Orientation

Outcomes:

- Understand what Vigilante does and does not do.
- Run the app locally.
- Validate the baseline test/spec workflow.

Tasks:

- Read `docs/onboarding/developer-onboarding.md`.
- Read all required files listed in the onboarding guide.
- Run:

```bash
make setup
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
make test
```

Deliverable:

- A short onboarding note with unclear areas, suspected risks, and one suggested
  first contribution.

## Day 2: Architecture and Test Mapping

Outcomes:

- Understand route, service, model, repository, and template boundaries.
- Identify how organization-scoped behavior is tested.

Tasks:

- Map one existing user workflow from route to service to repository to tests.
- Recommended workflow: case listing or case detail.
- Identify the relevant OpenSpec requirement.

Deliverable:

- A short markdown note in the PR or issue describing the mapped workflow and
  relevant test files.

## Day 3: First Spec-Backed Slice

Outcomes:

- Create or refine a small OpenSpec change before coding.

Recommended slice:

- Improve tests or documentation for organization-scoped case visibility or
  evidence provenance.

Tasks:

```bash
/opsx:propose <first-slice-name>
```

Deliverable:

- OpenSpec proposal, specs, design, and tasks for a small change.

## Day 4: Implementation

Outcomes:

- Implement the first small change.
- Keep the PR easy to review.

Tasks:

```bash
/opsx:apply <first-slice-name>
make test
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
```

Deliverable:

- PR with the small implementation, tests, and linked OpenSpec change.

## Day 5: Review, Cleanup, and Next Slice

Outcomes:

- Incorporate review.
- Archive or update the OpenSpec change.
- Propose the next small slice.

Tasks:

```bash
make check
/opsx:archive <first-slice-name>
```

Deliverable:

- Merged or review-ready PR.
- Proposed next task with risk level and expected value.

## Success Criteria

- The developer can run the project locally.
- The developer can explain the product boundary and current blockers.
- The developer can create and apply an OpenSpec change.
- The first PR is small, tested, and does not require production access.
- The developer follows evidence, organization-scope, and human-review rules.
