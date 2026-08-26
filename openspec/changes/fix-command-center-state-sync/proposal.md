## Why

The command center can show a city filter, alert list, map, and selected case that contradict one another. This weakens operator trust and can lead reviewers to act on a stale case that is outside the active filters.

## What Changes

- Make the filtered alert set the authoritative source for the alert list and command-center markers.
- Keep the selected case only while it remains inside the authoritative filtered set.
- Clear the selected-case inspector when filters produce no eligible alert, and show an explicit empty state instead of stale case data.
- Ensure marker selection cannot reactivate a filtered or paginated-out alert.
- Add regression coverage for city filtering, zero-result filters, pagination, and selection synchronization.
- Keep the existing static atlas and hard-coded marker positioning for this focused bug fix; replacing it with a geographic map is a separate change.

## Capabilities

### New Capabilities

- `command-center-state`: Defines the consistency contract between filters, visible alerts, command-center markers, pagination, and selected-case state.

### Modified Capabilities

None.

## Impact

- Affected UI: the command-center section of `app/templates/dashboard.html`.
- Affected tests: dashboard rendering and browser-state regression coverage in `tests/test_dashboard.py`.
- No persistence, authentication, authorization, infrastructure, Google integration, reporting, or enforcement changes.
- No new production dependency.
