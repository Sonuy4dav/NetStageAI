"""Quality checks and coverage summaries for the read-only case dataset."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .engine import DiagnosticEngine
from .models import DiagnosticCase


ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


@dataclass(frozen=True)
class DatasetSummary:
    total_cases: int
    case_ids: list[str]
    concepts: dict[str, int]
    severities: dict[str, int]
    osi_layers: dict[str, int]


def validate_dataset(cases_path: Path) -> list[str]:
    """Return validation errors without modifying the dataset."""
    errors: list[str] = []
    try:
        cases = DiagnosticEngine(cases_path).load_cases()
    except (OSError, ValueError) as error:
        return [str(error)]

    if not cases:
        errors.append("dataset must contain at least one case")

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("case_id values must be unique")

    for case in cases:
        if not case.expected_fault.strip():
            errors.append(f"{case.case_id}: expected_fault must be provided")
        if not case.osi_layer.strip():
            errors.append(f"{case.case_id}: osi_layer must be provided")
        if case.severity.upper() not in ALLOWED_SEVERITIES:
            errors.append(f"{case.case_id}: unsupported severity '{case.severity}'")

    return errors


def summarize_dataset(cases: list[DiagnosticCase]) -> DatasetSummary:
    """Create stable coverage counts for the loaded cases."""
    return DatasetSummary(
        total_cases=len(cases),
        case_ids=[case.case_id for case in cases],
        concepts=dict(sorted(Counter(case.concept_tag for case in cases).items())),
        severities=dict(sorted(Counter(case.severity for case in cases).items())),
        osi_layers=dict(sorted(Counter(case.osi_layer for case in cases).items())),
    )
