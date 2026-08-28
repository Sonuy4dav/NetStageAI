"""Regression checks for the current CSV and deterministic workflow."""

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.audit import record_decision
from src.checker import check_show_output, evaluate_show_output
from src.dataset import summarize_dataset, validate_dataset
from src.engine import DiagnosticEngine
from src.llm import LLMResponseError, build_diagnosis_prompt, parse_diagnosis_response
from src.models import AuditEvent, Diagnosis, ProposedCommand, RuleCheckResult, RuleFinding
from src.security import (
    MAX_CLI_OUTPUT_CHARS,
    audit_path_is_allowed,
    get_provider_api_key,
    sanitize_cli_output,
    validate_cli_output,
)


class SourceWorkflowTests(unittest.TestCase):
    def test_uploaded_dataset_and_net001(self) -> None:
        engine = DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv")
        cases = engine.load_cases()

        self.assertEqual(len(cases), 30)
        self.assertEqual(cases[0].case_id, "NET-001")
        self.assertEqual(cases[0].osi_layer, "Layer 3")

        diagnosis = engine.diagnose(cases[0])
        self.assertIn("administratively down", diagnosis.root_cause)
        self.assertEqual(diagnosis.fix_steps[0].command, "interface GigabitEthernet0/0.10")
        self.assertEqual(diagnosis.fix_steps[-1].command, "no shutdown")

    def test_invalid_csv_required_value_includes_row_number(self) -> None:
        path = Path(__file__).parent / "invalid_cases.csv"
        path.write_text(
            "case_id,symptom,topology_note,concept_tag,severity,show_outputs\n"
            "NET-BAD,,topology,tag,High,output\n",
            encoding="utf-8",
        )
        self.addCleanup(path.unlink)

        with self.assertRaisesRegex(ValueError, r"row 2.*symptom"):
            DiagnosticEngine(path).load_cases()

    def test_empty_output_has_no_findings(self) -> None:
        self.assertEqual(check_show_output(""), [])

    def test_uploaded_dataset_passes_phase_three_quality_gate(self) -> None:
        dataset_path = Path(__file__).parents[1] / "data" / "cases.csv"
        cases = DiagnosticEngine(dataset_path).load_cases()
        summary = summarize_dataset(cases)

        self.assertEqual(validate_dataset(dataset_path), [])
        self.assertEqual(summary.total_cases, 30)
        self.assertEqual(summary.case_ids, [f"NET-{number:03d}" for number in range(1, 31)])
        self.assertGreaterEqual(len(summary.concepts), 10)

    def test_contract_models_validate_and_serialize(self) -> None:
        diagnosis = Diagnosis(
            case_id="NET-001",
            root_cause="Interface is down",
            osi_layer="Layer 3",
            confidence=0.98,
        )
        self.assertEqual(diagnosis.as_dict()["case_id"], "NET-001")
        with self.assertRaisesRegex(ValueError, "confidence"):
            Diagnosis("NET-001", "Fault", "Layer 3", 1.1)
        with self.assertRaisesRegex(ValueError, "decision"):
            AuditEvent("NET-001", "PENDING", diagnosis, [])

    def test_structured_commands_and_diagnosis_serialization(self) -> None:
        diagnosis = Diagnosis(
            case_id="NET-001",
            root_cause="Interface is down",
            osi_layer="Layer 3",
            confidence=0.98,
            evidence=["interface is administratively down"],
            fix_steps=[ProposedCommand("no shutdown", "Enable the interface")],
        )

        self.assertEqual(diagnosis.fix_steps[0].command, "no shutdown")
        self.assertEqual(
            diagnosis.as_dict()["fix_steps"],
            [{"command": "no shutdown", "description": "Enable the interface"}],
        )

    def test_models_reject_invalid_osi_and_non_list_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "osi_layer"):
            Diagnosis("NET-001", "Fault", "Layer 8", 0.5)
        with self.assertRaisesRegex(ValueError, "evidence"):
            Diagnosis("NET-001", "Fault", "Layer 3", 0.5, evidence=("not-a-list",))

    def test_audit_event_writes_contract_fields(self) -> None:
        diagnosis = Diagnosis("NET-001", "Interface is down", "Layer 3", 0.98)
        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "audit.md"
            record_decision(
                log_path,
                AuditEvent("NET-001", "APPROVED", diagnosis, ["no shutdown"]),
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn('"case_id": "NET-001"', content)
        self.assertIn('"decision": "APPROVED"', content)
        self.assertIn('"human_override": false', content)
        self.assertIn('"error_information": {}', content)

    def test_audit_records_edit_rejection_and_error_information(self) -> None:
        diagnosis = Diagnosis("NET-001", "Interface is down", "Layer 3", 0.98)
        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "audit.md"
            record_decision(
                log_path,
                AuditEvent(
                    "NET-001",
                    "EDITED",
                    diagnosis,
                    ["no shutdown"],
                    ["description reviewed"],
                    True,
                ),
            )
            record_decision(
                log_path,
                AuditEvent(
                    "NET-001",
                    "REJECTED",
                    diagnosis,
                    ["no shutdown"],
                    error_information={"reason": "operator rejected remediation"},
                ),
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn('"decision": "EDITED"', content)
        self.assertIn('"decision": "REJECTED"', content)
        self.assertIn('"reason": "operator rejected remediation"', content)

    def test_invalid_audit_event_is_rejected_before_writing(self) -> None:
        diagnosis = Diagnosis("NET-001", "Interface is down", "Layer 3", 0.98)
        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "audit.md"
            with self.assertRaisesRegex(ValueError, "decision"):
                record_decision(
                    log_path,
                    AuditEvent("NET-001", "INVALID", diagnosis, []),
                )
            self.assertFalse(log_path.exists())

    def test_security_redacts_secrets_and_limits_cli_input(self) -> None:
        output = "username admin password=super-secret\nradius-server host 10.0.0.50 key shared-secret"
        sanitized = sanitize_cli_output(output)

        self.assertNotIn("super-secret", sanitized)
        self.assertNotIn("shared-secret", sanitized)
        with self.assertRaisesRegex(ValueError, "character limit"):
            validate_cli_output("x" * (MAX_CLI_OUTPUT_CHARS + 1))

    def test_security_uses_environment_key_and_restricts_audit_path(self) -> None:
        with patch.dict("os.environ", {"NETSTAGE_LLM_API_KEY": "test-key"}):
            self.assertEqual(get_provider_api_key(), "test-key")
        root = Path(__file__).parents[1]
        self.assertTrue(audit_path_is_allowed(root / "docs" / "model_audit_log.md", root))
        self.assertFalse(audit_path_is_allowed(root / "data" / "other.md", root))

    def test_phase_four_matches_each_uploaded_case_once(self) -> None:
        cases = DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()

        for case in cases:
            result = evaluate_show_output(case.show_outputs)
            self.assertEqual(result.status, "ERRORS_DETECTED", case.case_id)
            self.assertEqual(len(result.findings), 1, case.case_id)
            self.assertTrue(result.findings[0].rule_id)
            self.assertTrue(result.findings[0].severity)

    def test_phase_four_unknown_output_returns_no_known_error(self) -> None:
        result = evaluate_show_output("show version\nCisco IOS Software, unknown lab output")

        self.assertEqual(result.status, "NO_KNOWN_ERROR")
        self.assertEqual(result.findings, [])

    def test_phase_twelve_rule_does_not_false_positive_on_similar_text(self) -> None:
        result = evaluate_show_output(
            "GigabitEthernet0/0.10 is down, line protocol is down"
        )

        self.assertEqual(result.status, "NO_KNOWN_ERROR")
        self.assertEqual(result.findings, [])

    def test_phase_twelve_every_case_has_a_complete_diagnosis(self) -> None:
        cases = DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()
        engine = DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv")

        for case in cases:
            diagnosis = engine.diagnose(case)
            self.assertEqual(diagnosis.case_id, case.case_id)
            self.assertTrue(diagnosis.root_cause, case.case_id)
            self.assertTrue(diagnosis.osi_layer, case.case_id)
            self.assertGreaterEqual(diagnosis.confidence, 0.0)
            self.assertLessEqual(diagnosis.confidence, 1.0)
            self.assertIsInstance(diagnosis.evidence, list)
            self.assertIsInstance(diagnosis.fix_steps, list)

    def test_phase_six_unknown_case_uses_safe_fallback(self) -> None:
        case = replace(
            DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()[0],
            show_outputs="show version with no known diagnostic pattern",
        )

        diagnosis = DiagnosticEngine(Path("data/cases.csv")).diagnose(case)

        self.assertEqual(diagnosis.source, "deterministic_fallback")
        self.assertEqual(diagnosis.confidence, 0.0)
        self.assertEqual(diagnosis.fix_steps, [])

    def test_phase_six_uses_typed_llm_result_when_required(self) -> None:
        case = replace(
            DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()[0],
            show_outputs="ambiguous evidence",
            requires_llm=True,
        )
        expected = Diagnosis("NET-001", "LLM root cause", "Layer 3", 0.75, source="llm")
        engine = DiagnosticEngine(Path("data/cases.csv"), llm_diagnoser=lambda _: expected)

        diagnosis = engine.diagnose(case)

        self.assertEqual(diagnosis, expected)

    def test_phase_six_handles_llm_unavailable_and_invalid_results(self) -> None:
        case = replace(
            DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()[0],
            show_outputs="ambiguous evidence",
            requires_llm=True,
        )
        unavailable = DiagnosticEngine(Path("data/cases.csv")).diagnose(case)
        invalid = DiagnosticEngine(Path("data/cases.csv"), llm_diagnoser=lambda _: "not a diagnosis").diagnose(case)  # type: ignore[arg-type]

        self.assertEqual(unavailable.source, "llm_unavailable")
        self.assertEqual(invalid.source, "llm_invalid")
        self.assertEqual(unavailable.fix_steps, [])
        self.assertEqual(invalid.fix_steps, [])

    def test_phase_six_conflicting_findings_are_safe(self) -> None:
        case = DiagnosticEngine(Path(__file__).parents[1] / "data" / "cases.csv").load_cases()[0]
        findings = [
            RuleFinding("RULE_A", "First finding", ["evidence A"], [], "Layer 3", 0.8),
            RuleFinding("RULE_B", "Second finding", ["evidence B"], [], "Layer 3", 0.8),
        ]
        with patch("src.engine.evaluate_show_output", return_value=RuleCheckResult("ERRORS_DETECTED", findings)):
            diagnosis = DiagnosticEngine(Path("data/cases.csv")).diagnose(case)

        self.assertEqual(diagnosis.source, "deterministic_conflict")
        self.assertEqual(diagnosis.confidence, 0.0)
        self.assertEqual(diagnosis.fix_steps, [])

    def test_phase_seven_prompt_contains_required_case_context(self) -> None:
        case = DiagnosticEngine(Path("data/cases.csv")).load_cases()[0]
        prompt = build_diagnosis_prompt(case, evaluate_show_output(case.show_outputs))

        self.assertIn(case.symptom, prompt)
        self.assertIn(case.topology_note, prompt)
        self.assertIn(case.show_outputs, prompt)
        self.assertIn("known_rule_results", prompt)
        self.assertIn("required_json_schema", prompt)
        self.assertIn("Return JSON only", prompt)

    def test_phase_seven_valid_json_is_parsed_into_typed_diagnosis(self) -> None:
        response = '{"case_id":"NET-X","root_cause":"Unknown route","osi_layer":"Layer 3","confidence":0.75,"evidence":["show output"],"next_command":"show ip route","fix_steps":[{"command":"show ip route"}],"source":"llm"}'

        diagnosis = parse_diagnosis_response(response, "NET-X")

        self.assertEqual(diagnosis.source, "llm")
        self.assertIsInstance(diagnosis.fix_steps[0], ProposedCommand)

    def test_phase_seven_invalid_json_is_rejected(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_diagnosis_response("not json", "NET-X")
        with self.assertRaises(LLMResponseError):
            parse_diagnosis_response(
                '{"case_id":"NET-X","root_cause":"Fault","osi_layer":"Layer 3","confidence":0.5,"evidence":[],"next_command":"show version","fix_steps":[{"command":3}]}',
                "NET-X",
            )

    def test_phase_seven_engine_handles_timeout_api_error_and_deterministic_only(self) -> None:
        case = replace(
            DiagnosticEngine(Path("data/cases.csv")).load_cases()[0],
            show_outputs="ambiguous evidence",
            requires_llm=True,
        )
        timeout = DiagnosticEngine(Path("data/cases.csv"), llm_diagnoser=lambda _: (_ for _ in ()).throw(TimeoutError())).diagnose(case)
        api_error = DiagnosticEngine(Path("data/cases.csv"), llm_diagnoser=lambda _: (_ for _ in ()).throw(ConnectionError())).diagnose(case)
        deterministic = DiagnosticEngine(Path("data/cases.csv"), deterministic_only=True, llm_diagnoser=lambda _: "should not run").diagnose(case)

        self.assertEqual(timeout.source, "llm_timeout")
        self.assertEqual(api_error.source, "llm_api_error")
        self.assertEqual(deterministic.source, "deterministic_only")


if __name__ == "__main__":
    unittest.main()