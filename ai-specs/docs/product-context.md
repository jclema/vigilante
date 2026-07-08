# Vigilante Product Context

Vigilante is a pilot for detecting impersonation of authorized dealers on
Google Maps, Google Business Profile, and Google Places. The current public
product is WatchmanHub at `https://www.watchmanhub.com`.

## Problem

Dealers, retail networks, brands, and marketplaces in fraud-prone markets can
be harmed by cloned locations, fake branches, manipulated photos, phishing
inside Maps, and confusing public listings. The manual process to detect,
compare, document, triage, and escalate those incidents is slow and weakly
traceable.

## Users

- Platform operators who monitor all networks and coordinate case handling.
- Network managers who supervise multiple dealers or branches.
- Dealer admins who review alerts for their organization.
- Dealer members who help validate local evidence and operational context.
- Future brand, marketplace, legal, compliance, and trust-and-safety teams.

## Current Value

- Public scan flow for suspicious Google Places results.
- Case management, triage, timeline, and evidence dossier.
- Server-rendered operations dashboard for platform, network, and dealer views.
- Organization hierarchy for platform, network, dealer, and branch contexts.
- GBP connection and customer media flow implemented in software, currently
  blocked externally by Google API approval and quota.
- Browser capture and guided enforcement exist as experimental human-in-the-loop
  tooling, not authoritative evidence.

## Product Position

Vigilante is not autonomous enforcement. It is an operations product that helps
humans detect suspicious public listings, assemble evidence, score risk, decide
next action, and preserve follow-up history.

## Strategic Direction

The highest-value path is to become a repeatable trust-and-safety operating
system for vulnerable local-commerce ecosystems, especially in developing
markets where public map fraud creates real operational and reputational harm.

Near-term product growth should focus on:

- More reliable public detection and false-positive control.
- Clear case review workflows and audit trails.
- Evidence provenance and chain-of-custody quality.
- Operational metrics: alert precision, false positives, triage time, decision
  time, case outcome, and value per protected organization.
- Practical fallbacks for blocked Google API access.

## Constraints

- Google Maps public pages are unstable for automation and can trigger bot
  defenses.
- GBP customer media access is currently blocked externally despite software
  readiness.
- Production runs on Google Cloud and should keep Cloud Run, Cloud Armor,
  Secret Manager, Scheduler, Firestore, and Cloud Storage boundaries explicit.
- Irreversible external reports or enforcement actions require human approval.
