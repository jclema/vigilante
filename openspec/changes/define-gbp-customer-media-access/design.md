## Context

The current codebase has a formal GBP connection and customer media path in
software, but real customer media access is blocked externally by Google access
approval and quota. Prior browser automation experiments are unreliable in
Cloud Run and must not be treated as authoritative GBP evidence.

Google's Business Profile documentation says the APIs allow merchants or their
representatives to manage Business Profile account and location data, including
user-created data such as photos, posts, and reviews. The docs also state that
quota can be `0` when API access has not been granted and point developers to
the basic access application path instead of requesting a quota increase.

## Approach

This change defines the work contract, not the final implementation.

The developer must first verify:

- exact API surface for customer-uploaded media
- OAuth scopes and consent screen requirements
- account/location ownership or manager permissions required
- access approval path for the current Google Cloud project
- quota state and remediation path
- whether the current API exposes enough media metadata for manipulation review
- privacy and retention obligations for storing fetched media or derivatives

If official access is confirmed, the implementation should extend the existing
organization-level GBP connection and location binding flow. If access remains
blocked, the product should use a clearly labeled human-reviewed fallback.

## Evidence Model Expectations

Official GBP media evidence must preserve:

- organization ID
- GBP account and location identifiers
- media resource identifier or source URL when available
- fetch timestamp
- case association when attached to a case
- reliability label: official GBP media
- hash or comparable integrity marker when bytes are stored
- operator-visible explanation of why the image matters

Fallback evidence must preserve the same provenance standard but use a different
reliability label and must not be displayed as official GBP media.

## Non-Goals

- No Google Maps scraping implementation.
- No bypass of Google approval, quota, authentication, or terms.
- No automatic external reporting or enforcement.
- No production secret, IAM, Terraform, or persistence schema change in this spec-only change.

## Verification

- Validate OpenSpec artifacts.
- Review the developer work brief.
- Future implementation must include focused tests for authorization, blocked
  access state, evidence provenance, and fallback labeling.
