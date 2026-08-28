# NetStage AI Data Contracts

Phase 2 defines the input and output shapes used by the application. The uploaded `data/cases.csv` file is not modified.

## CSV case contract

Required columns:

```text
case_id,symptom,topology_note,concept_tag,severity,show_outputs
```

Optional columns:

```text
expected_fault,osi_layer,expected_osi_layer,expected_evidence,expected_commands,requires_llm
```

`expected_osi_layer` is accepted as the canonical name; `osi_layer` is retained for compatibility with the current dataset. List fields use semicolons as separators. `requires_llm` accepts `true`, `false`, `1`, `0`, `yes`, or `no` and defaults to `false` when empty.

Validation behavior:

- Missing required headers are rejected.
- Unsupported headers are rejected.
- Required text values cannot be empty.
- Duplicate `case_id` values are rejected.
- Invalid boolean values are rejected.
- Errors include the CSV row number.

## Rule result contract

```json
{
  "status": "ERRORS_DETECTED",
  "rule_id": "INTERFACE_ADMIN_DOWN",
  "message": "GigabitEthernet0/0.30 is administratively down.",
  "evidence": ["..."],
  "fix_steps": ["..."],
  "osi_layer": "Layer 3 - Network",
  "confidence": 0.98
  ,"severity": "HIGH"
}
```

`confidence` must be a number from `0` through `1`.
The evaluator returns `NO_KNOWN_ERROR` with an empty `findings` list when no rule matches. Rule severity is one of `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.

## Diagnostic result contract

```json
{
  "case_id": "NET-001",
  "root_cause": "Subinterface is administratively down",
  "osi_layer": "Layer 3 - Network",
  "confidence": 0.98,
  "evidence": ["GigabitEthernet0/0.30 is administratively down"],
  "next_command": "show running-config interface GigabitEthernet0/0.30",
  "fix_steps": [
    {"command": "configure terminal"},
    {"command": "interface GigabitEthernet0/0.30"},
    {"command": "no shutdown"}
  ],
  "source": "deterministic_rule"
}
```

## Audit log contract

Each Markdown entry contains JSON with `timestamp`, `case_id`, `decision`, `diagnosis`, `original_commands`, `edited_commands`, `human_override`, and `error_information`. `decision` must be `APPROVED`, `EDITED`, or `REJECTED`. Commands are recorded only; they are never executed by this prototype. Events are validated before writing and flushed to disk as one complete Markdown entry.