# Diagnostic Engine

Phase 6 is implemented by `src/engine.py`.

The engine follows this order:

1. Load and validate cases through the Phase 2 CSV contract.
2. Run deterministic rules through `evaluate_show_output()`.
3. Convert one complete finding into the typed `Diagnosis` model.
4. Send an LLM-required case to the optional typed `llm_diagnoser` provider.
5. Return a safe typed fallback when no rule matches, the provider is unavailable, the provider fails, or its result is invalid.
6. Refuse remediation when multiple deterministic findings conflict or a finding has no evidence.

The LLM provider must be a callable that accepts the constructed prompt string and returns either JSON text or a validated `Diagnosis`. The engine does not accept arbitrary dictionaries and never executes proposed commands.