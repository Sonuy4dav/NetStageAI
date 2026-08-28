"""Shared data models for NetStage AI."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .security import validate_cli_output


ALLOWED_OSI_LAYERS = {
    "Unknown",
    "Layer 1",
    "Layer 2",
    "Layer 3",
    "Layer 4",
    "Layer 5",
    "Layer 6",
    "Layer 7",
    "Layer 2/3",
    "Layer 3/4",
}


@dataclass(frozen=True)
class DiagnosticCase:
    case_id: str
    symptom: str
    topology_note: str
    concept_tag: str
    severity: str
    show_outputs: str
    expected_fault: str = ""
    osi_layer: str = ""
    expected_evidence: list[str] = field(default_factory=list)
    expected_commands: list[str] = field(default_factory=list)
    requires_llm: bool = False

    def __post_init__(self) -> None:
        _require_text(self.case_id, "case_id")
        _require_text(self.symptom, "symptom")
        _require_text(self.topology_note, "topology_note")
        _require_text(self.concept_tag, "concept_tag")
        _require_text(self.severity, "severity")
        validate_cli_output(self.show_outputs)
        if self.osi_layer:
            _require_osi_layer(self.osi_layer)
        _require_string_list(self.expected_evidence, "expected_evidence")
        _require_string_list(self.expected_commands, "expected_commands")


@dataclass(frozen=True)
class ProposedCommand:
    """A configuration command shown to a human for review."""

    command: str
    description: str = ""

    def __post_init__(self) -> None:
        _require_text(self.command, "command")
        if not isinstance(self.description, str):
            raise ValueError("description must be a string")

    def as_dict(self) -> dict[str, str]:
        result = {"command": self.command}
        if self.description:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    message: str
    evidence: list[str] = field(default_factory=list)
    fix_steps: list[ProposedCommand] = field(default_factory=list)
    osi_layer: str = ""
    confidence: float = 0.0
    severity: str = "MEDIUM"

    def __post_init__(self) -> None:
        _require_text(self.rule_id, "rule_id")
        _require_text(self.message, "message")
        _require_confidence(self.confidence)
        _require_osi_layer(self.osi_layer)
        _require_string_list(self.evidence, "evidence")
        object.__setattr__(self, "fix_steps", _coerce_commands(self.fix_steps))

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "evidence": self.evidence,
            "suggested_fix": [command.as_dict() for command in self.fix_steps],
            "osi_layer": self.osi_layer,
            "confidence": self.confidence,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class RuleCheckResult:
    status: str
    findings: list[RuleFinding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self.status}
        if self.findings:
            result["findings"] = [finding.as_dict() for finding in self.findings]
        return result


@dataclass(frozen=True)
class Diagnosis:
    case_id: str
    root_cause: str
    osi_layer: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    next_command: str = ""
    fix_steps: list[ProposedCommand] = field(default_factory=list)
    source: str = "deterministic_rule"

    def __post_init__(self) -> None:
        _require_text(self.case_id, "case_id")
        _require_text(self.root_cause, "root_cause")
        _require_osi_layer(self.osi_layer)
        _require_confidence(self.confidence)
        _require_text(self.source, "source")
        _require_string_list(self.evidence, "evidence")
        object.__setattr__(self, "fix_steps", _coerce_commands(self.fix_steps))

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "root_cause": self.root_cause,
            "osi_layer": self.osi_layer,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "next_command": self.next_command,
            "fix_steps": [command.as_dict() for command in self.fix_steps],
            "source": self.source,
        }


@dataclass(frozen=True)
class AuditEvent:
    case_id: str
    decision: str
    diagnosis: Diagnosis
    original_commands: list[ProposedCommand]
    edited_commands: list[ProposedCommand] = field(default_factory=list)
    human_override: bool = False
    error_information: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        _require_text(self.case_id, "case_id")
        if self.decision not in {"APPROVED", "REJECTED", "EDITED"}:
            raise ValueError("decision must be APPROVED, REJECTED, or EDITED")
        _require_text(self.timestamp, "timestamp")
        if not isinstance(self.error_information, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in self.error_information.items()
        ):
            raise ValueError("error_information must be a dictionary of strings")
        object.__setattr__(self, "original_commands", _coerce_commands(self.original_commands))
        object.__setattr__(self, "edited_commands", _coerce_commands(self.edited_commands))


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_confidence(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")
    if not 0 <= value <= 1:
        raise ValueError("confidence must be between 0 and 1")


def _require_osi_layer(value: str) -> None:
    if value not in ALLOWED_OSI_LAYERS:
        raise ValueError(
            "osi_layer must be one of: " + ", ".join(sorted(ALLOWED_OSI_LAYERS))
        )


def _require_string_list(value: object, field_name: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"{field_name} must be a list of strings")


def _coerce_commands(value: object) -> list[ProposedCommand]:
    if not isinstance(value, list):
        raise ValueError("commands must be a list")
    commands: list[ProposedCommand] = []
    for item in value:
        if isinstance(item, ProposedCommand):
            commands.append(item)
        elif isinstance(item, str):
            commands.append(ProposedCommand(item))
        else:
            raise ValueError("commands must contain strings or ProposedCommand objects")
    return commands
