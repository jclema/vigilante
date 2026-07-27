# External Developer Access Policy

This policy defines the recommended access path for an external developer.

## Phase 1: Repository-Only Access

Allowed:

- GitHub repository read/write access.
- Pull request creation.
- Local demo environment using `.env.example`.
- Public docs and OpenSpec artifacts.
- Explicitly provisioned `developer_viewer` web-app access when product walkthrough access is required.

Not allowed:

- Google Cloud project access.
- Secret Manager access.
- Production `.env` values.
- Production OAuth credentials.
- Customer evidence exports.
- Browser storage state.
- Service account keys.
- Web-app settings, mutations, reporting, enforcement, and integration administration.

Goal:

- Let the developer understand the project and ship a low-risk first PR.

## Phase 2: Limited Operational Visibility

Allowed only after a successful first PR:

- Read-only operational context if needed.
- Sanitized logs or screenshots.
- Staging or demo credentials if available.

Still not allowed by default:

- Production secret access.
- IAM changes.
- Terraform changes.
- Direct production deploy permissions.
- Real customer evidence access.

Goal:

- Enable debugging and implementation without exposing sensitive assets.

## Phase 3: Elevated Access

Requires explicit approval.

May include:

- Limited Google Cloud viewer role.
- Access to selected non-secret production diagnostics.
- Participation in deployment review.

Requires:

- NDA.
- Contractor or work-for-hire agreement.
- IP assignment terms.
- Security expectations in writing.
- Clear scope of work.

## Mandatory Rules

- No credentials, evidence, browser sessions, service accounts, or `.env` files
  in Git.
- No production changes without explicit approval.
- No destructive cleanup, retention changes, IAM changes, or Terraform changes
  without review.
- No automatic external reporting or enforcement without human approval.
- No customer data should be shared outside approved channels.
- Developer viewer access is network-wide but read-only and must be revoked when
  the engagement ends.

## Developer Viewer Provisioning

Dry run:

```bash
STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
  python -m scripts.provision_developer_viewer \
  --full-name "Trystan Jaquet" \
  --email "trystan.jaquet@gmail.com"
```

Apply only after the authorization release is deployed:

```bash
STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
  python -m scripts.provision_developer_viewer \
  --full-name "Trystan Jaquet" \
  --email "trystan.jaquet@gmail.com" \
  --apply
```

The developer then signs in at `https://www.watchmanhub.com` with the exact
Google account that was provisioned. Do not send a temporary password.

Verification:

- Dashboard and case views load across the Yamaha network.
- `/settings` returns `403`.
- Representative case, report, scan, and browser-enforcement writes return
  `403` without changing state.
- No Google Cloud IAM, Firestore console, Secret Manager, or deployment access
  is granted.

To revoke access, deactivate the user or remove its `developer_viewer`
membership from the application repository. Revoke immediately when the
engagement ends or the approved scope changes.

## Pull Request Requirements

Every PR from an external developer should include:

- Linked OpenSpec change or spec.
- Product/user workflow affected.
- Test commands run.
- Risk notes.
- Screenshots for UI changes.
- Confirmation that no secrets or customer evidence were included.
