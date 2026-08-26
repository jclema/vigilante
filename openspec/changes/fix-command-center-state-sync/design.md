## Context

See `proposal.md` for motivation. The command center is server-rendered and enhanced by one inline script. Alert rows, markers, pagination, filters, and the selected-case inspector currently maintain overlapping state. `renderCommandPage()` hides rows and markers, while `selectCommandCase()` only accepts a row and cannot clear stale details.

The existing map is a Medellin atlas with manually positioned markers. This change must restore truthful state without adding the Leaflet dependency or changing backend data contracts.

## Goals / Non-Goals

**Goals:**

- Establish one reconciliation step after every filter or pagination transition.
- Make the current visible alert page the source of truth for markers and selection.
- Render explicit list, map, and inspector empty states.
- Prevent the Medellin atlas from impersonating Bogotá geography.
- Preserve the current server-rendered architecture and URL filter behavior.

**Non-Goals:**

- Geographic marker placement, Leaflet, tile providers, clustering, or map panning.
- Backend, persistence, authorization, reporting, or external integration changes.
- General dashboard redesign or mobile navigation changes.

## Decisions

### Reconcile after rendering the filtered page

`renderCommandPage()` will return the rows visible on the current page. A dedicated reconciliation function will use that returned set to update selection and empty-state presentation.

This is preferred over querying `hidden` state from multiple callbacks because it makes the transition order explicit: filter, paginate, render markers, reconcile selection.

### Allow case selection to be cleared

`selectCommandCase()` will accept no row as the canonical clear operation. It will remove list and marker selection, hide populated case details, show the empty inspector, and remove actionable links from focus.

This is preferred over keeping the last case visible because stale operational context is more dangerous than an empty inspector.

### Keep selection only inside the current page

If the selected alert remains on the rendered page, it remains selected. Otherwise the first visible row becomes selected. Pagination therefore moves selection to the new page rather than leaving a hidden case active.

### Guard the static atlas by supported context

The existing atlas remains visible for the all-cities overview and Medellin metro-area cities. For Bogotá, the atlas and manually positioned markers are suppressed and replaced by a contextual map state. This avoids fabricated geography until the separate geographic-map change is implemented.

### Test rendered contracts and browser behavior

Fast tests will assert the required DOM hooks and reconciliation logic in the server-rendered template. A real-browser check will verify the Bogotá zero-result transition and recovery to a city with alerts at desktop and mobile widths.

## Risks / Trade-offs

- [Risk] Template-string tests can become coupled to implementation details. → Keep assertions focused on observable hooks and state transitions, then add browser verification for the critical flow.
- [Risk] The temporary Bogotá map state is less visually rich than the atlas. → Prefer truthful absence over incorrect geography and replace it in the later Leaflet change.
- [Risk] Inline JavaScript remains large. → Keep this patch local; frontend modularization belongs to a separate change.

## Migration Plan

1. Add failing regression tests for clearable selection, zero-result states, and unsupported-atlas handling.
2. Add the minimal DOM states and reconciliation logic.
3. Run focused dashboard tests, then the complete project checks.
4. Verify the filter transition in a local authenticated browser at desktop and mobile widths.

Rollback is a normal code revert. There are no schema or data migrations.
