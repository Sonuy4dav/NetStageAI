"""Provider-neutral prompt construction and strict LLM response parsing."""

import json
from json import JSONDecodeError
from typing import Any

from .checker import RuleCheckResult
from .models import DiagnosticCase, Diagnosis, ProposedCommand
from .security import sanitize_cli_output, validate_cli_output


DIAGNOSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "case_id",
        "root_cause",
        "osi_layer",
        "confidence",
        "evidence",
        "next_command",
        "fix_steps",
    ],
    "properties": {
        "case_id": {"type": "string"},
        "root_cause": {"type": "string"},
        "osi_layer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "next_command": {"type": "string"},
        "fix_steps": {"type": "array"},
        "source": {"type": "string"},
    },
}


class LLMResponseError(ValueError):
    """Raised when an LLM response is not valid diagnostic JSON."""


def build_diagnosis_prompt(case: DiagnosticCase, rule_result: RuleCheckResult) -> str:
    """Build the complete prompt sent to an LLM provider."""
    validate_cli_output(case.show_outputs)
    payload = {
        "case_id": case.case_id,
        "symptom": case.symptom,
        "topology_note": case.topology_note,
        "cli_output": sanitize_cli_output(case.show_outputs),
        "known_rule_results": rule_result.as_dict(),
        "required_json_schema": DIAGNOSIS_SCHEMA,
    }
    return (
        "Analyze this network case. Return JSON only. Proposed commands are for "
        "human review and must never be executed by you or the application.\n\n"
        + json.dumps(payload, indent=2)
    )


def parse_diagnosis_response(response: str, expected_case_id: str) -> Diagnosis:
    """Parse and validate strict JSON returned by an LLM provider."""
    if not isinstance(response, str) or not response.strip():
        raise LLMResponseError("LLM response must be a non-empty JSON string")
    try:
        payload = json.loads(response)
    except JSONDecodeError as error:
        raise LLMResponseError("LLM response is not valid JSON") from error
    if not isinstance(payload, dict):
        raise LLMResponseError("LLM response must be a JSON object")

    required = set(DIAGNOSIS_SCHEMA["required"])
    missing = required - set(payload)
    if missing:
        raise LLMResponseError("LLM response is missing fields: " + ", ".join(sorted(missing)))
    unsupported = set(payload) - (required | {"source"})
    if unsupported:
        raise LLMResponseError("LLM response contains unsupported fields: " + ", ".join(sorted(unsupported)))
    if payload["case_id"] != expected_case_id:
        raise LLMResponseError("LLM response case_id does not match the selected case")

    fix_steps = payload["fix_steps"]
    if not isinstance(fix_steps, list):
        raise LLMResponseError("fix_steps must be a JSON array")
    commands: list[ProposedCommand] = []
    for item in fix_steps:
        try:
            if isinstance(item, str):
                commands.append(ProposedCommand(item))
            elif isinstance(item, dict) and set(item) <= {"command", "description"}:
                commands.append(ProposedCommand(item.get("command", ""), item.get("description", "")))
            else:
                raise LLMResponseError("each fix_steps item must be a command string or object")
        except (TypeError, ValueError) as error:
            raise LLMResponseError("each fix_steps item must contain a valid command") from error

    try:
        return Diagnosis(
            case_id=payload["case_id"],
            root_cause=payload["root_cause"],
            osi_layer=payload["osi_layer"],
            confidence=payload["confidence"],
            evidence=payload["evidence"],
            next_command=payload["next_command"],
            fix_steps=commands,
            source="llm",
        )
    except (TypeError, ValueError) as error:
        raise LLMResponseError(f"LLM response failed schema validation: {error}") from error
