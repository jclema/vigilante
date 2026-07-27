## 1. Authorization Contract

- [x] 1.1 Add the `developer_viewer` role and explicit actor capabilities for network visibility, case mutation, sensitive settings, organization management, and platform management; verify with focused auth unit tests.
- [x] 1.2 Add reusable route guards for case visibility and mutation authorization; verify unauthorized and developer-viewer requests fail closed.

## 2. Read-Only Product Access

- [x] 2.1 Apply visibility and mutation guards to case, report, scan, browser-enforcement, integration, notification, membership, and configuration routes; verify representative developer-viewer POST requests return `403` without side effects.
- [x] 2.2 Require authenticated, scoped access for evidence media and sensitive operational resources; verify unauthenticated and out-of-scope reads are denied.
- [x] 2.3 Update templates and navigation so developer viewers can inspect supported dashboards and cases without seeing action or settings controls; verify rendered HTML for the role.

## 3. Provisioning and Operations

- [x] 3.1 Add an idempotent, dry-run-capable provisioning script for developer viewer memberships without logging credentials; verify it against the in-memory repository.
- [x] 3.2 Document provisioning, Google sign-in, verification, monitoring, and revocation in the onboarding and production runbooks; verify commands are copy-pasteable.

## 4. Verification and Release

- [x] 4.1 Run focused authorization tests, `make check`, and OpenSpec validation; resolve all failures without weakening security controls.
- [ ] 4.2 Commit, push, and open a reviewed PR before deployment; verify required GitHub checks pass.
- [ ] 4.3 Deploy the approved revision, provision Trystan Jaquet as `developer_viewer`, and verify read access plus `403` mutation checks in production.
