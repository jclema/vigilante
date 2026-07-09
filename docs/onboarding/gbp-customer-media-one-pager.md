# GBP Customer Media Access One-Pager

## Why We Are Bringing You In

We are bringing you into Vigilante / WatchmanHub to help solve the product's
highest-value technical blocker: accessing or monitoring user-uploaded Google
Business Profile photos for authorized Yamaha dealer locations in a safe,
reliable, and Google-compliant way.

Bad actors are modifying storefront photos with AI and inserting fake phone
numbers onto Yamaha dealer facades. Customers see those manipulated photos on
Google Maps or Search, call the fraudulent number, and can be redirected into
scams, phishing, or fake sales conversations.

The goal is not to build a scraper. The goal is to validate and implement the
official, compliant path.

## Formal Spec

Start with the OpenSpec change:

- `openspec/changes/define-gbp-customer-media-access/proposal.md`
- `openspec/changes/define-gbp-customer-media-access/design.md`
- `openspec/changes/define-gbp-customer-media-access/specs/gbp-integration/spec.md`
- `openspec/changes/define-gbp-customer-media-access/specs/evidence/spec.md`
- `openspec/changes/define-gbp-customer-media-access/tasks.md`

Then read the active work brief:

- `docs/plans/active/gbp-customer-media-access.md`

## Current Product Context

Vigilante is an assisted operations product, not an autonomous enforcement
system. It helps operators:

- monitor suspicious Google Maps / Places activity
- compare public listings against authorized dealer data
- collect and preserve evidence
- create and manage cases
- score operational risk
- support a human decision to escalate, archive, or report

The product already has a FastAPI backend, server-rendered dashboard,
organization-scoped access, case management, evidence timeline, public Places
clone detection, and a GBP connection flow implemented in software.

## Current Blocker

The formal GBP customer media path exists in code, but real access is blocked
externally by Google approval and quota.

The key question is:

Can we retrieve or monitor customer-uploaded GBP photos for locations owned or
managed by authorized Yamaha dealers through an official Google Business Profile
API path?

If yes, we need the exact requirements. If no, we need a compliant fallback
workflow.

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

## What We Need From You

Produce a short technical recommendation that answers:

- Can customer-uploaded GBP photos be retrieved through official APIs?
- Which endpoint or API surface applies?
- What Google Cloud project setup is required?
- What Business Profile API access approval is required?
- What OAuth scopes and user permissions are required?
- What is the current quota state and how do we resolve `Requests per minute = 0`?
- What are the known API limitations for customer media?
- What are the privacy, retention, and evidence-handling implications?
- What implementation gaps exist in the current codebase?
- What fallback workflow should we use if official access remains unavailable?

## Guardrails

Do not:

- bypass Google restrictions
- depend on fragile Google Maps scraping as the main solution
- treat browser capture as official GBP evidence
- automate external reports without human approval
- commit credentials, tokens, browser state, or customer evidence
- change production infrastructure or secrets without explicit approval

Always preserve:

- organization-level authorization
- evidence provenance
- demo versus production separation
- human review before enforcement
- Google-compliant access patterns

## Expected First Deliverable

Your first deliverable should be a technical recommendation, not implementation.

It should include:

- conclusion: official access possible, blocked, or uncertain
- cited Google docs
- required scopes, permissions, API surfaces, approval steps, and quota steps
- implementation plan if official access is confirmed
- fallback plan if official access is blocked
- risks and questions that need business or legal review

## Success Criteria

We should be able to decide:

- whether to implement official GBP customer media retrieval now
- whether we first need Google approval, quota, or verification work
- what to build in Vigilante if access is approved
- what fallback to operate if access is blocked
- how to preserve evidence provenance and human review either way
