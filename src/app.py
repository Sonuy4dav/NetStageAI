"""NetStage AI Streamlit entry point."""

from pathlib import Path
import json

import streamlit as st

from src.audit import record_decision
from src.checker import evaluate_show_output
from src.dataset import validate_dataset
from src.engine import DiagnosticEngine
from src.logging_config import configure_logging
from src.models import AuditEvent
from src.security import sanitize_cli_output


PROJECT_ROOT = Path(__file__).resolve().parent.parent
with (PROJECT_ROOT / "system_config.json").open(encoding="utf-8") as config_file:
    CONFIG = json.load(config_file)
engine = DiagnosticEngine(
    PROJECT_ROOT / "data" / "cases.csv",
    deterministic_only=bool(CONFIG.get("deterministic_only", True)),
)
logger = configure_logging()


st.set_page_config(
    page_title="NetStage AI",
    page_icon=":satellite:",
    layout="wide",
)

st.title("NetStage AI")
st.subheader("Cisco network diagnostic assistant")
st.warning("Prototype only: commands are analyzed and recorded, never executed on network devices.")

try:
    cases = engine.load_cases()
except (OSError, ValueError) as error:
    logger.exception("Unable to load diagnostic cases")
    st.error(f"Unable to load diagnostic cases: {error}")
    cases = []

dataset_errors = validate_dataset(PROJECT_ROOT / "data" / "cases.csv")
if dataset_errors:
    st.warning("Dataset quality checks found issues: " + "; ".join(dataset_errors))
else:
    st.success(f"Dataset quality check passed: {len(cases)} cases loaded.")

with st.sidebar:
    st.header("Case Selection")
    selected_case_id = st.selectbox(
        "Diagnostic case",
        [case.case_id for case in cases] or ["No cases loaded"],
    )

if cases:
    selected_case = next(case for case in cases if case.case_id == selected_case_id)
    if st.session_state.get("active_case_id") != selected_case.case_id:
        st.session_state.active_case_id = selected_case.case_id
        st.session_state.pop("diagnosis", None)
        st.session_state.pop("diagnosis_error", None)
        st.session_state.pop("rule_result", None)
        st.session_state.pop("editing_commands", None)
        st.session_state.pop("edited_commands", None)
        st.session_state.pop("pending_decision", None)
        st.session_state.pop("final_decision", None)

    st.header(f"Case {selected_case.case_id}")
    st.write(f"**Case ID:** {selected_case.case_id}")
    st.write(f"**Symptom:** {selected_case.symptom}")
    st.write(f"**Topology:** {selected_case.topology_note}")
    st.write(f"**Severity:** {selected_case.severity}")
    st.code(sanitize_cli_output(selected_case.show_outputs), language="text")

    if st.button("Run Diagnosis", type="primary"):
        try:
            with st.spinner("Running deterministic checks and diagnosis..."):
                st.session_state.rule_result = evaluate_show_output(selected_case.show_outputs)
                st.session_state.diagnosis = engine.diagnose(selected_case)
            st.session_state.pop("diagnosis_error", None)
            logger.info("Diagnosis generated for case %s", selected_case.case_id)
        except Exception as error:
            logger.exception("Diagnosis failed for case %s", selected_case.case_id)
            st.session_state.pop("diagnosis", None)
            st.session_state.diagnosis_error = str(error)

    if st.session_state.get("diagnosis_error"):
        st.error(f"Diagnosis could not be completed: {st.session_state.diagnosis_error}")

    rule_result = st.session_state.get("rule_result")
    if rule_result:
        st.subheader("Detected errors")
        if rule_result.findings:
            for finding in rule_result.findings:
                st.warning(f"[{finding.severity}] {finding.rule_id}: {finding.message}")
        else:
            st.info("No known deterministic errors detected.")

    diagnosis = st.session_state.get("diagnosis")
    if diagnosis and diagnosis.case_id == selected_case.case_id:
        st.header("Diagnosis")
        st.write(f"**Root cause:** {diagnosis.root_cause}")
        st.write(f"**OSI layer:** {diagnosis.osi_layer}")
        st.write(f"**Confidence:** {diagnosis.confidence:.0%}")
        rule_status = "ERRORS_DETECTED" if diagnosis.evidence else "NO_KNOWN_ERROR"
        st.write(f"**Rule status:** {rule_status}")
        st.write("**Evidence:**")
        for evidence in diagnosis.evidence:
            st.code(evidence, language="text")
        st.write(f"**Next command:** `{diagnosis.next_command}`")
        st.write("**Proposed fix:**")
        case_key = selected_case.case_id
        original_commands = [command.command for command in diagnosis.fix_steps]
        edited_commands = st.session_state.get("edited_commands", original_commands)
        st.write("**Original commands:**")
        st.code("\n".join(original_commands) or "No deterministic fix available.", language="text")

        if edited_commands != original_commands:
            st.write("**Edited commands:**")
            st.code("\n".join(edited_commands), language="text")

        editing = st.session_state.get("editing_commands", False)
        if st.button("Edit Commands", key=f"edit_{case_key}"):
            st.session_state.editing_commands = True
            st.rerun()

        if editing:
            command_text = st.text_area(
                "Edit proposed commands",
                value="\n".join(edited_commands),
                height=140,
                key=f"commands_{case_key}",
            )
            if st.button("Save Edited Commands", key=f"save_edit_{case_key}"):
                saved_commands = [
                    line for line in command_text.splitlines() if line.strip()
                ]
                try:
                    original_commands = [command.command for command in diagnosis.fix_steps]
                    record_decision(
                        PROJECT_ROOT / "docs" / "model_audit_log.md",
                        AuditEvent(
                            case_id=case_key,
                            decision="EDITED",
                            diagnosis=diagnosis,
                            original_commands=diagnosis.fix_steps,
                            edited_commands=saved_commands,
                            human_override=saved_commands != original_commands,
                        ),
                            project_root=PROJECT_ROOT,
                    )
                    st.session_state.edited_commands = saved_commands
                    st.session_state.editing_commands = False
                    logger.info("Command edit recorded for case %s", case_key)
                    st.rerun()
                except Exception as error:
                    logger.exception("Command edit recording failed for case %s", case_key)
                    st.error(f"Command edit could not be recorded: {error}")

        if st.session_state.get("final_decision"):
            st.success(f"Final decision: {st.session_state.final_decision}")
        else:
            action_columns = st.columns(2)
            with action_columns[0]:
                if st.button("Approve Fix", type="primary", key=f"approve_{case_key}"):
                    st.session_state.pending_decision = "APPROVED"
                    st.rerun()
            with action_columns[1]:
                if st.button("Reject Fix", key=f"reject_{case_key}"):
                    st.session_state.pending_decision = "REJECTED"
                    st.rerun()

        pending_decision = st.session_state.get("pending_decision")
        if pending_decision and not st.session_state.get("final_decision"):
            st.warning(f"Confirm final decision: {pending_decision}")
            confirmed = st.checkbox(
                "I reviewed the diagnosis and proposed commands.",
                key=f"confirm_{pending_decision}_{case_key}",
            )
            confirmation_label = (
                "Confirm Approve Fix" if pending_decision == "APPROVED" else "Confirm Reject Fix"
            )
            if st.button(confirmation_label, key=f"confirm_action_{pending_decision}_{case_key}"):
                if pending_decision == "APPROVED" and not confirmed:
                    st.error("Approval requires explicit confirmation.")
                elif not confirmed:
                    st.error("Please confirm that you reviewed the diagnosis.")
                else:
                    try:
                        record_decision(
                            PROJECT_ROOT / "docs" / "model_audit_log.md",
                            AuditEvent(
                                case_id=case_key,
                                decision=pending_decision,
                                diagnosis=diagnosis,
                                original_commands=diagnosis.fix_steps,
                                edited_commands=edited_commands
                                if edited_commands != original_commands
                                else [],
                                human_override=edited_commands != original_commands,
                            ),
                            project_root=PROJECT_ROOT,
                        )
                        st.session_state.final_decision = pending_decision
                        st.session_state.pending_decision = None
                        logger.info("Decision recorded for case %s: %s", case_key, pending_decision)
                        st.rerun()
                    except Exception as error:
                        logger.exception("Decision recording failed for case %s", case_key)
                        st.error(f"Decision could not be recorded: {error}")
