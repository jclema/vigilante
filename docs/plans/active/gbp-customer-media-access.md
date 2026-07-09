# GBP Customer Media Access Work Brief

## Problem

Bad actors are modifying user-uploaded Google Business Profile photos for
authorized Yamaha dealers. The manipulated images can place fake phone numbers
on storefront facades, causing customers to call fraudulent numbers from Google
Maps or Search.

Vigilante needs a safe, reliable, and Google-compliant way to access or monitor
customer-uploaded GBP photos for locations owned or managed by authorized
dealer organizations.

## Primary Goal

Determine and implement the correct official path for GBP customer media access.

The first deliverable is not a scraper. The first deliverable is a verified
technical recommendation based on Google's current Business Profile API
capabilities, access requirements, OAuth scopes, quota state, and compliance
rules.

## Official Sources To Review First

- Google Business Profile APIs overview:
  https://developers.google.com/my-business/content/overview
- Google Business Profile API quota limits:
  https://developers.google.com/my-business/content/limits
- Google Business Profile `accounts.locations.media` reference:
  https://developers.google.com/my-business/reference/rest/v4/accounts.locations.media
- Google Business Profile API FAQ:
  https://developers.google.com/my-business/content/faq
- Google Business Profile API change log:
  https://developers.google.com/my-business/content/change-log

## Non-Goals

- Do not build or depend on fragile Google Maps scraping as the main solution.
- Do not bypass Google restrictions or quota gates.
- Do not treat browser capture as official GBP evidence.
- Do not automate external reporting or enforcement.
- Do not store customer evidence without explicit provenance and access rules.

## Expected Research Output

The external developer should produce a short technical recommendation covering:

- whether customer-uploaded GBP photos can be retrieved through official APIs
- which endpoint or API surface applies
- required Google Cloud project setup
- required Business Profile API access approval
- required OAuth scopes and user permissions
- quota state and how to resolve `Requests per minute = 0`
- known API limitations for customer media
- data retention and privacy implications
- implementation gaps in the current codebase
- fallback workflow if official access remains unavailable

## Implementation Direction If Official Access Is Confirmed

- Use organization-level OAuth for authorized dealer admins.
- Bind GBP accounts and locations to Vigilante organizations.
- Fetch only media for locations the organization owns or manages.
- Store metadata, thumbnails or evidence references only as needed.
- Preserve source URL/API resource name, fetched timestamp, location ID, case ID,
  hash if applicable, and reliability context.
- Show operators which evidence is official GBP media versus fallback evidence.
- Keep human approval before any external report or enforcement action.

## Fallback Direction If Official Access Is Blocked

If official access is blocked by Google approval, quota, or API limitations:

- keep the blocked state visible in settings
- define a manual or semi-automated review workflow
- allow authorized humans to attach evidence with explicit provenance
- avoid presenting fallback evidence as official GBP customer media
- document the blocker and next reapplication steps for Google

## Acceptance Criteria

- A developer can explain the official Google-compliant path or why it is blocked.
- The recommendation cites the specific Google API docs and access requirements.
- Any implementation plan preserves organization-level authorization and evidence provenance.
- Browser automation is explicitly treated as experimental fallback only.
- The plan includes tests, observability, failure modes, and rollback or disable strategy.
