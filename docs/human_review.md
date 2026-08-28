# Human Review Workflow

Phase 9 requires an explicit human decision after a diagnosis exists.

1. Review the diagnosis, evidence, next command, and original commands.
2. Use `Edit Commands` and `Save Edited Commands` when changes are needed.
3. Choose `Approve Fix` or `Reject Fix`.
4. Confirm that the diagnosis and commands were reviewed.
5. Saving an edit writes an `EDITED` audit record.
6. The final decision is written to the audit log with any edited commands and override status.

The workflow only records proposed commands. It never connects to or changes a real network device.

The dashboard displays a prototype-only warning, redacts common credentials from CLI output, and writes only to the configured audit file.