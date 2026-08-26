## 1. Regression Coverage

- [x] 1.1 Add dashboard regression assertions for clearable selection, explicit zero-result hooks, filtered marker reconciliation, and unsupported-atlas handling; verify the focused tests fail before implementation.

## 2. Command Center State

- [x] 2.1 Add accessible empty states for the alert list, command map, and case inspector; verify dashboard rendering exposes the expected hooks.
- [x] 2.2 Reconcile filters, pagination, markers, and selected-case state from the current visible alert page; verify focused dashboard tests pass.
- [x] 2.3 Guard the Medellin atlas when Bogotá is selected and restore it for supported contexts; verify the Bogotá and recovery browser flows.

## 3. Verification

- [x] 3.1 Verify the synchronized command-center flow at desktop and mobile widths using local demo authentication.
- [x] 3.2 Run `make check` and `npx --yes @fission-ai/openspec@latest validate fix-command-center-state-sync --no-interactive` successfully.
