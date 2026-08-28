# Security and Safety Controls

Phase 11 boundaries:

- Proposed commands are typed data and are never executed.
- The dashboard displays an explicit prototype-only warning.
- Common passwords, secrets, tokens, API keys, enable secrets, and RADIUS keys are redacted before display and LLM prompting.
- CLI output is limited to 12,000 characters.
- Loaded case data is validated by the Phase 2 and Phase 3 contracts.
- CLI output is treated as evidence, not instructions.
- Provider keys are read from environment variables such as `NETSTAGE_LLM_API_KEY`, never from project data files.
- `system_config.json` enables deterministic-only mode by default and defines the LLM timeout setting for future providers.
- Production audit writes are restricted to `docs/model_audit_log.md` under the project root.
- LLM timeout and API-error paths return safe typed fallback results.