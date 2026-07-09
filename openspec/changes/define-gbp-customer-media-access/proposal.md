## Why

Fraud actors are modifying customer-uploaded Google Business Profile photos for
authorized Yamaha dealers, including storefront images with fake phone numbers.
Vigilante needs a safe, reliable, and Google-compliant way to access or monitor
those photos so operators can detect manipulation and preserve evidence.

## What Changes

- Define the official research and implementation contract for GBP customer media access.
- Require the developer to verify current Google API capabilities, OAuth scopes,
  access approval, quota state, and compliance limits before implementation.
- Add evidence requirements for official GBP media versus fallback evidence.
- Add a product brief for the external developer.
- Keep runtime behavior unchanged in this change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `gbp-integration`: Adds requirements for official customer media access research, access gating, and fallback behavior.
- `evidence`: Adds requirements for GBP customer media provenance and manipulated-photo handling.

## Impact

- Adds `docs/plans/active/gbp-customer-media-access.md`.
- Adds OpenSpec delta specs for `gbp-integration` and `evidence`.
- No application code, production dependency, schema, infrastructure, IAM, or secret changes.
