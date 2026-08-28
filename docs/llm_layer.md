# LLM Diagnostic Layer

Phase 7 is provider-neutral. The application builds a prompt with the selected case's symptom, topology note, CLI output, known deterministic rule results, and the required diagnosis schema.

`src/llm.py` provides:

- `build_diagnosis_prompt()` for complete JSON-only prompts.
- `parse_diagnosis_response()` for strict JSON and typed `Diagnosis` validation.
- `LLMResponseError` for malformed JSON, missing fields, unsupported fields, wrong case IDs, invalid confidence, invalid OSI layers, invalid evidence, and invalid commands.

`DiagnosticEngine` accepts an optional provider callable. The provider receives the prompt string and may return JSON text or a validated `Diagnosis`. Provider failures are converted to safe typed results with sources such as `llm_timeout`, `llm_api_error`, `llm_invalid`, or `llm_error`.

When `deterministic_only=True`, LLM calls are skipped and the engine returns a safe `deterministic_only` result. Suggested commands are displayed for human review only; the application never executes them.
