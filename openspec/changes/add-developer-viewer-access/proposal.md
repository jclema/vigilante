## Why

An external developer needs to inspect the complete Yamaha operating experience in production without gaining the ability to change customer data, configuration, reports, enforcement state, integrations, or platform administration. The current roles do not provide network-wide read-only access, so granting an existing role would violate least privilege.

## What Changes

- Add a `developer_viewer` role with network-wide visibility across Yamaha organizations.
- Enforce read-only authorization on every state-changing web and API route.
- Allow the role to sign in with an explicitly provisioned Google account.
- Sanitize or deny access to secrets, credentials, browser session state, and other privileged operational configuration.
- Add regression tests proving the viewer can inspect the application and receives `403` for state-changing actions.
- Document provisioning, review, and revocation of developer viewer access.
- Non-goals: granting Google Cloud IAM, Secret Manager, Firestore console, deployment, Terraform, GBP administration, automated reporting, or enforcement permissions.

## Capabilities

### New Capabilities

- `developer-viewer-access`: Network-wide, read-only application access for explicitly provisioned development collaborators.

### Modified Capabilities

- `case-management`: Require explicit write authorization for case mutations, report generation, and browser-enforcement actions.
- `evidence`: Require authenticated, organization-authorized access to evidence media.
- `operations`: Distinguish network visibility from platform, organization, integration, and operational mutation permissions.

## Impact

Affected areas include role and actor models, route authorization, evidence delivery, case/report/enforcement APIs, settings UI, Firestore user memberships, authentication tests, dashboard tests, production access documentation, and the user provisioning workflow. No new dependency, persistence collection, cloud role, secret, or infrastructure resource is introduced.
