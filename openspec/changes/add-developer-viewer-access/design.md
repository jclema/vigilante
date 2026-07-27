## Context

WatchmanHub currently derives both visibility and mutation authority from four business roles. `yamaha_admin` provides the closest visibility match for a developer who must inspect the full Yamaha network, but it is not a read-only contract. Several case, report, evidence, and browser-enforcement routes require authentication without enforcing organization scope or mutation permission. Google sign-in also creates users before a membership is assigned, so access must remain explicitly provisioned.

The first intended user is Trystan Jaquet (`trystan.jaquet@gmail.com`). The design must remain reusable for future development collaborators and must not encode a personal email in application configuration.

## Goals / Non-Goals

**Goals:**

- Provide explicitly provisioned, network-wide, read-only product access.
- Separate visibility permission from mutation and administration permission.
- Enforce authorization server-side for HTML and API routes.
- Preserve organization scoping and evidence provenance.
- Make provisioning and revocation auditable and repeatable.

**Non-Goals:**

- Grant Google Cloud, Firestore console, Secret Manager, Cloudflare, deployment, IAM, Terraform, GBP administration, reporting, or enforcement access.
- Create a general-purpose custom-role engine.
- Change existing business-role visibility beyond closing authorization gaps.
- Introduce a new Firestore collection or external dependency.

## Decisions

### Add a first-class `developer_viewer` membership role

`UserRole.DEVELOPER_VIEWER` will be treated as network-visible but never as platform-admin, organization-admin, or mutation-authorized. A first-class role keeps the persisted membership explicit and compatible with the existing user, membership, and Firestore serialization model.

Alternative considered: assign `yamaha_admin` and rely on UI discipline. Rejected because hidden controls do not prevent direct API mutations and the role does not express the intended security boundary.

### Introduce explicit actor capabilities

`ActorContext` will expose separate capabilities for network visibility, operational mutation, organization management, and platform management. State-changing routes will require the appropriate capability instead of relying on authentication alone.

Alternative considered: scatter direct role comparisons across routes. Rejected because it is harder to audit and likely to drift as routes are added.

### Default all authenticated users to no network mutation

Network read visibility does not imply write access. Existing organization administrators retain management for their own organization, Yamaha administrators retain human operational actions, and developer viewers are denied every write operation. Route helpers will enforce case visibility before reads and mutation permission before writes.

### Protect evidence delivery as an authenticated, scoped resource

Evidence image routes will require an actor and verify that the artifact's case or organization is visible to the actor. Missing scope information fails closed for developer viewers. Evidence responses do not expose storage credentials or raw browser session state.

### Provision through a controlled script

A repository script will upsert the user and a `developer_viewer` membership in the platform organization using the configured production repository. It will accept identity fields as explicit arguments, avoid printing credentials, and support a dry run. Google sign-in then links the pre-provisioned user by normalized email.

Alternative considered: use the existing organization invitation form. Rejected because the form exposes business roles, generates a temporary password, and is not designed for network-wide read-only memberships.

### Keep sensitive settings unavailable

Developer viewers can use product dashboards and case/evidence views but cannot access settings pages or APIs that expose integrations, memberships, notification targets, browser sessions, or operational credentials.

## Risks / Trade-offs

- [Missed mutation route] → Inventory all non-GET routes and add negative authorization tests for case, report, browser, scan, integration, notification, membership, and configuration actions.
- [Sensitive data remains visible in legitimate read views] → Limit this role to product-level data already intended for Yamaha network review and deny settings, raw session state, and secret-bearing resources.
- [Role serialization breaks existing Firestore data] → Add the enum value without changing existing values or membership schema, and test repository round trips.
- [Google sign-in creates an unscoped account before provisioning] → Require pre-provisioning for usable access and ensure users without memberships cannot reach application data.
- [Operational debugging needs exceed app visibility] → Keep Google Cloud access as a separate, explicitly approved phase.

## Migration Plan

1. Deploy the role and authorization checks before provisioning any developer viewer.
2. Run the full test suite and explicit negative authorization tests.
3. Provision Trystan's normalized Google email with a `developer_viewer` membership.
4. Ask Trystan to sign in through Google and verify dashboard, case, and evidence reads.
5. Verify representative mutation attempts return `403` and no production state changes.
6. Monitor authentication and authorization failures during the first session.

Rollback: deactivate or remove the developer membership first, then roll Cloud Run back to the previous known-good revision if the authorization release causes a regression. The additive enum value does not require a data migration.

## Open Questions

None for the initial release. Google Cloud diagnostic access remains a separate decision after the first contribution.
