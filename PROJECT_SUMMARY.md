# NetStage AI Project Summary

## Project Overview

NetStage AI is a Streamlit-based Cisco network troubleshooting assistant for
Cisco IOS and Packet Tracer lab scenarios. It analyzes predefined CLI output,
identifies known configuration or connectivity problems, and presents
possible remediation commands for human review.

The project is an MVP/prototype. It does not connect to network devices,
execute commands, or automatically deploy configuration changes.

## Work Completed

- Built a Streamlit web interface for selecting and reviewing diagnostic cases.
- Added a CSV-based dataset containing 30 network troubleshooting cases.
- Implemented CSV loading with required-field, duplicate-ID, and value
  validation.
- Added dataset quality checks for expected faults, OSI layers, severities, and
  case coverage summaries.
- Implemented 30 deterministic Cisco diagnostic rules covering common issues
  across OSI Layers 2, 3, 4, and 7.
- Added rule statuses for `ERRORS_DETECTED` and `NO_KNOWN_ERROR`.
- Added evidence, severity, confidence, OSI layer, next-command, and proposed
  fix information to diagnoses.
- Added safe handling for multiple matching rules through a
  `deterministic_conflict` diagnosis with no automatic fix.
- Added safe fallback diagnoses when no known rule matches or a diagnosis is
  incomplete.
- Added provider-neutral LLM prompt construction and strict JSON response
  parsing.
- Added LLM failure handling for unavailable providers, timeouts, connection
  errors, invalid JSON, invalid schema data, and mismatched case IDs.
- Added typed data models for cases, findings, diagnoses, proposed commands,
  and audit events.
- Added a human-in-the-loop workflow to approve, reject, or edit proposed
  commands.
- Added confirmation requirements before recording approval or rejection.
- Added Markdown audit logging for decisions, edited commands, overrides, and
  error information.
- Added CLI input validation with a 12,000-character limit.
- Added redaction for common passwords, secrets, tokens, API keys, and RADIUS
  keys before display or LLM prompt construction.
- Added environment-based API key lookup without storing credentials in project
  files.
- Added audit path restrictions so records can only be written to the approved
  project audit log.
- Added application logging for dataset loading, diagnosis, edits, and review
  decisions.
- Added project documentation covering the data contract, diagnostic engine,
  rule engine, LLM layer, security, testing, human review, and audit history.
- Added regression tests for dataset validation, all bundled cases, rule
  matching, false-positive protection, diagnosis fallbacks, LLM parsing,
  security behavior, and audit logging.

## Main Components

| Component | Purpose |
| --- | --- |
| `src/app.py` | Streamlit user interface and review workflow |
| `src/dataset.py` | Dataset validation and coverage summaries |
| `src/checker.py` | Deterministic Cisco rule evaluation |
| `src/engine.py` | Diagnosis orchestration and fallback behavior |
| `src/models.py` | Validated application data models |
| `src/llm.py` | LLM prompt generation and response validation |
| `src/security.py` | Input limits, secret redaction, and path controls |
| `src/audit.py` | Human decision audit logging |
| `data/cases.csv` | 30 predefined diagnostic scenarios |
| `tests/test_source_workflow.py` | Automated regression coverage |

## Current Configuration

The project is configured for deterministic-only operation:

- LLM integration is disabled by default.
- LLM timeout metadata is set to 30 seconds.
- CLI output is limited to 12,000 characters.
- Audit records are written to `docs/model_audit_log.md`.
- The application uses Python 3.10 or newer, Streamlit, and pandas.

## Typical User Workflow

1. Start the Streamlit application.
2. Select one of the predefined cases.
3. Review the symptom, topology, severity, and sanitized CLI output.
4. Run the diagnosis.
5. Review the detected issue, evidence, confidence, next command, and fix.
6. Approve, reject, or edit the proposed commands.
7. Confirm the decision.
8. Review the recorded decision in the audit log.

## Testing

The regression suite is run with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests verify the complete source workflow, including the 30 bundled cases,
security boundaries, deterministic diagnosis behavior, LLM contracts, and
human review audit records.

## Remaining Prototype Limitations

- No live SSH, Telnet, API, or device connection is implemented.
- Proposed commands are never executed automatically.
- No production LLM provider adapter is wired in.
- The case dataset is predefined rather than user-managed through the UI.
- Audit history is stored in Markdown instead of a database.
- Deterministic rules only recognize known output patterns.
- `NO_KNOWN_ERROR` does not prove that a network is healthy.
- Human verification is required before any proposed remediation is accepted.

## Overall Status

The project has a functional and tested MVP diagnostic workflow with explicit
safety boundaries, structured outputs, deterministic rule coverage, optional
LLM extension points, human review, and auditability. It is ready for local
demonstration and further development toward provider integration or live-lab
connectivity.