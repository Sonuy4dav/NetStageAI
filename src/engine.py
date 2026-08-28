"""Case loading and diagnostic orchestration."""

import csv
from pathlib import Path
from typing import Callable

from .checker import evaluate_show_output
from .llm import LLMResponseError, build_diagnosis_prompt, parse_diagnosis_response
from .models import DiagnosticCase, Diagnosis, RuleCheckResult, RuleFinding


LLMDiagnoser = Callable[[str], str | Diagnosis]


REQUIRED_CASE_FIELDS = {
    "case_id",
    "symptom",
    "topology_note",
    "concept_tag",
    "severity",
    "show_outputs",
}
OPTIONAL_CASE_FIELDS = {
    "expected_fault",
    "osi_layer",
    "expected_osi_layer",
    "expected_evidence",
    "expected_commands",
    "requires_llm",
}


class DiagnosticEngine:
    """Load cases and produce deterministic diagnoses."""

    def __init__(
        self,
        cases_path: Path,
        llm_diagnoser: LLMDiagnoser | None = None,
        deterministic_only: bool = False,
    ) -> None:
        self.cases_path = cases_path
        self.llm_diagnoser = llm_diagnoser
        self.deterministic_only = deterministic_only

    def load_cases(self) -> list[DiagnosticCase]:
        with self.cases_path.open(newline="", encoding="utf-8") as cases_file:
            reader = csv.DictReader(cases_file)
            headers = set(reader.fieldnames or [])
            missing_fields = REQUIRED_CASE_FIELDS - headers
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ValueError(f"cases.csv is missing required fields: {missing}")

            unknown_fields = headers - REQUIRED_CASE_FIELDS - OPTIONAL_CASE_FIELDS
            if unknown_fields:
                unknown = ", ".join(sorted(unknown_fields))
                raise ValueError(f"cases.csv contains unsupported fields: {unknown}")

            cases = []
            seen_ids: set[str] = set()
            for row_number, row in enumerate(reader, start=2):
                try:
                    case = _case_from_row(row)
                except ValueError as error:
                    raise ValueError(f"Invalid cases.csv row {row_number}: {error}") from error
                if case.case_id in seen_ids:
                    raise ValueError(f"Invalid cases.csv row {row_number}: duplicate case_id {case.case_id}")
                seen_ids.add(case.case_id)
                cases.append(case)
            return cases

    def diagnose(self, case: DiagnosticCase) -> Diagnosis:
        rule_result = evaluate_show_output(case.show_outputs)
        findings = rule_result.findings
        if len(findings) > 1:
            return _conflict_diagnosis(case, findings)
        if findings:
            finding = findings[0]
            if not finding.evidence:
                return _incomplete_diagnosis(case, finding)
            return _diagnosis_from_finding(case, finding)
        if case.requires_llm:
            return self._diagnose_with_llm(case, rule_result)
        return _fallback_diagnosis(case, "No known deterministic fault detected.")

    def _diagnose_with_llm(self, case: DiagnosticCase, rule_result: RuleCheckResult) -> Diagnosis:
        if self.deterministic_only:
            return _fallback_diagnosis(case, "Deterministic-only mode is enabled; LLM diagnosis was skipped.", "deterministic_only")
        if self.llm_diagnoser is None:
            return _fallback_diagnosis(case, "LLM diagnosis is required but unavailable.", "llm_unavailable")
        prompt = build_diagnosis_prompt(case, rule_result)
        try:
            response = self.llm_diagnoser(prompt)
        except TimeoutError:
            return _fallback_diagnosis(case, "LLM diagnosis timed out; human investigation is required.", "llm_timeout")
        except (ConnectionError, OSError):
            return _fallback_diagnosis(case, "LLM service error; human investigation is required.", "llm_api_error")
        except Exception:
            return _fallback_diagnosis(case, "LLM diagnosis failed; human investigation is required.", "llm_error")
        if isinstance(response, Diagnosis):
            diagnosis = response
        elif isinstance(response, str):
            try:
                diagnosis = parse_diagnosis_response(response, case.case_id)
            except LLMResponseError:
                return _fallback_diagnosis(case, "LLM returned invalid diagnostic JSON; human investigation is required.", "llm_invalid")
        else:
            return _fallback_diagnosis(case, "LLM returned an invalid diagnosis; human investigation is required.", "llm_invalid")
        if diagnosis.case_id != case.case_id:
            return _fallback_diagnosis(case, "LLM returned an invalid diagnosis; human investigation is required.", "llm_invalid")
        return diagnosis


def _diagnosis_from_finding(case: DiagnosticCase, finding: RuleFinding) -> Diagnosis:
    evidence = finding.evidence[0]
    return Diagnosis(
        case_id=case.case_id,
        root_cause=finding.message,
        osi_layer=case.osi_layer or finding.osi_layer,
        confidence=finding.confidence,
        evidence=finding.evidence,
        next_command=_next_command(finding.rule_id, evidence),
        fix_steps=finding.fix_steps,
        source="deterministic_rule",
    )


def _fallback_diagnosis(case: DiagnosticCase, root_cause: str, source: str = "deterministic_fallback") -> Diagnosis:
    return Diagnosis(
        case_id=case.case_id,
        root_cause=root_cause,
        osi_layer=case.osi_layer or "Unknown",
        confidence=0.0,
        evidence=[],
        next_command="show running-config",
        fix_steps=[],
        source=source,
    )


def _incomplete_diagnosis(case: DiagnosticCase, finding: RuleFinding) -> Diagnosis:
    return _fallback_diagnosis(
        case,
        f"Rule {finding.rule_id} matched but did not provide supporting evidence.",
        "deterministic_incomplete",
    )


def _conflict_diagnosis(case: DiagnosticCase, findings: list[RuleFinding]) -> Diagnosis:
    rule_ids = ", ".join(finding.rule_id for finding in findings)
    evidence = [evidence for finding in findings for evidence in finding.evidence]
    return Diagnosis(
        case_id=case.case_id,
        root_cause=f"Conflicting deterministic findings: {rule_ids}.",
        osi_layer=case.osi_layer or "Unknown",
        confidence=0.0,
        evidence=evidence,
        next_command="show running-config",
        fix_steps=[],
        source="deterministic_conflict",
    )


def _next_command(rule_id: str, evidence: str) -> str:
    if rule_id == "INTERFACE_ADMIN_DOWN" and " is " in evidence:
        interface = evidence.split(" is ", maxsplit=1)[0]
        return f"show running-config interface {interface}"
    return "show running-config"


def _case_from_row(row: dict[str, str | None]) -> DiagnosticCase:
    def text(field_name: str, required: bool = False) -> str:
        value = (row.get(field_name) or "").strip()
        if required and not value:
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    requires_llm = text("requires_llm").lower()
    if requires_llm not in {"", "true", "false", "1", "0", "yes", "no"}:
        raise ValueError("requires_llm must be true/false")

    return DiagnosticCase(
        case_id=text("case_id", required=True),
        symptom=text("symptom", required=True),
        topology_note=text("topology_note", required=True),
        concept_tag=text("concept_tag", required=True),
        severity=text("severity", required=True),
        show_outputs=text("show_outputs", required=True),
        expected_fault=text("expected_fault"),
        osi_layer=text("expected_osi_layer") or text("osi_layer"),
        expected_evidence=_split_contract_list(text("expected_evidence")),
        expected_commands=_split_contract_list(text("expected_commands")),
        requires_llm=requires_llm in {"true", "1", "yes"},
    )


def _split_contract_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]
