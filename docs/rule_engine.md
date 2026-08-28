# Deterministic Rule Engine

Phase 4 evaluates Cisco IOS and Packet Tracer evidence without an LLM. Rules are independent definitions in `src/checker.py`; each definition has a rule ID, targeted matcher, message, severity, OSI layer, confidence, and suggested remediation.

`evaluate_show_output()` returns:

- `ERRORS_DETECTED` with one or more structured findings when rules match.
- `NO_KNOWN_ERROR` with no findings when the evidence does not match a known rule.

The legacy `check_show_output()` helper remains available and returns only the findings list.

Rules require distinctive evidence phrases or combinations of phrases to reduce accidental matches. They generate suggested commands as text only. The application never executes these commands.

The current uploaded dataset has one targeted rule for each of `NET-001` through `NET-030`. The dataset remains read-only.