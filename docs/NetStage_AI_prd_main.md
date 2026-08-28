# NetSage AI --- Product Requirements Document (PRD)

**Version:** 1.0\
**Project Type:** MVP / Prototype Web Application\
**Development Scope:** Single-developer project\
**Target Environment:** Cisco IOS / Cisco Packet Tracer\
**Primary Interface:** Streamlit

------------------------------------------------------------------------

## 1. Product Overview

NetSage AI is an AI-assisted network diagnostic prototype that helps
users identify common network configuration problems from structured
Cisco Packet Tracer / Cisco IOS `show` command outputs.

The system combines:

-   Deterministic rule-based checks
-   LLM-based diagnostic reasoning
-   Structured JSON responses
-   Human-in-the-Loop (HITL) verification
-   Basic audit logging

The goal is to demonstrate the complete diagnostic workflow in a simple
web application. It is **not intended to be a production network
automation platform**.

------------------------------------------------------------------------

## 2. Problem Statement

Network troubleshooting can require:

-   Manual execution of many CLI `show` commands
-   Knowledge of multiple OSI layers
-   Careful analysis of verbose command output
-   Manual verification before applying configuration fixes

AI-generated network commands can also be risky if the model produces
incorrect or hallucinated commands.

NetSage AI addresses this by combining deterministic checks with AI
reasoning and requiring human approval before a proposed fix is
accepted.

------------------------------------------------------------------------

## 3. Product Goal

Build a simple, working MVP where a user can:

1.  Select a predefined network troubleshooting case.
2.  View the network symptom, topology information, and CLI output.
3.  Run deterministic diagnostic checks.
4.  Generate an AI-assisted diagnosis when required.
5.  View the root cause, OSI layer, confidence, evidence, and fix steps.
6.  Review the proposed CLI commands.
7.  Approve, edit, or reject the proposed fix.
8.  Record the decision in an audit log.

------------------------------------------------------------------------

## 4. Target Users

### Primary Users

-   Network engineering students
-   Cisco Packet Tracer learners
-   Network lab operators
-   Beginner/intermediate network engineers

### MVP User

A student or operator working with predefined Cisco Packet Tracer
troubleshooting scenarios.

------------------------------------------------------------------------

## 5. MVP Scope

### In Scope

-   Predefined network diagnostic cases
-   CSV-based case dataset
-   Deterministic rule checker
-   LLM diagnostic layer
-   Structured diagnostic output
-   Streamlit dashboard
-   Human approval workflow
-   Edit proposed commands
-   Reject/approve decisions
-   Basic audit logging
-   Inter-VLAN routing diagnostic example

### Out of Scope

The MVP will NOT implement:

-   Real physical router deployment
-   SSH/Telnet connection to live devices
-   Automatic configuration of real network equipment
-   Real-time network monitoring
-   Enterprise authentication
-   Distributed architecture
-   Kubernetes
-   Production cloud infrastructure
-   High-availability systems
-   Complex databases
-   Full MLOps infrastructure
-   Automatic unattended remediation

------------------------------------------------------------------------

## 6. Core Features

### 6.1 Case Selection

The dashboard should allow the user to select a diagnostic case such as:

`NET-001`

Each case contains:

-   `case_id`
-   `symptom`
-   `topology_note`
-   `concept_tag`
-   `severity`
-   `show_outputs`
-   `expected_fault`

The MVP dataset contains approximately 30 structured test cases.

------------------------------------------------------------------------

### 6.2 Deterministic Rule Checker

The rule engine analyzes CLI output using predefined rules and patterns.

Example checks:

-   Interface administratively down
-   Missing NAT overload
-   Mismatched VLAN IDs
-   Other known status/configuration patterns defined in the dataset

The checker should return a clear status such as:

`ERRORS_DETECTED`

or

`NO_KNOWN_ERROR`

The deterministic checker should be used wherever a known rule can
reliably identify a problem.

------------------------------------------------------------------------

### 6.3 LLM Diagnosis

When deterministic rules cannot fully explain the case, the system can
pass the relevant information to the prompt engine.

The prompt should instruct the model to:

-   Identify the likely OSI layer
-   Determine the root cause
-   Extract supporting evidence
-   Provide confidence
-   Suggest the next diagnostic command
-   Provide remediation steps
-   Return structured JSON

The LLM should assist diagnosis rather than directly control a network
device.

------------------------------------------------------------------------

### 6.4 Structured Diagnostic Output

The diagnostic result should follow a consistent structure:

``` json
{
  "root_cause": "",
  "osi_layer": "",
  "confidence": 0,
  "evidence": [],
  "next_command": "",
  "fix_steps": []
}
```

The exact values will depend on the selected case.

------------------------------------------------------------------------

### 6.5 Human-in-the-Loop Gate

The user must review the diagnosis before accepting the proposed fix.

The dashboard should provide three actions:

-   **Approve & Deploy**
-   **Edit Commands**
-   **Reject**

For the MVP, "Deploy" means recording the approved action for the
lab/prototype workflow. It does not mean automatically connecting to or
modifying a real network device.

------------------------------------------------------------------------

### 6.6 Audit Logging

The system should record important decisions such as:

-   Case ID
-   Diagnostic result
-   Operator decision
-   Edited commands, when applicable
-   Rejected/approved status
-   Human overrides

The audit log can be stored in a simple Markdown file:

`docs/model_audit_log.md`

------------------------------------------------------------------------

## 7. Primary MVP Use Case

### UC-01: Inter-VLAN Routing Diagnosis

**Scenario:**

`PC1 cannot reach Server1 in VLAN 30.`

Example CLI evidence:

``` text
GigabitEthernet0/0.10 is up, line protocol is up
GigabitEthernet0/0.30 is administratively down, line protocol is down
```

The system should:

1.  Load the selected case.
2.  Display the symptom and CLI output.
3.  Run the deterministic checker.
4.  Detect that `GigabitEthernet0/0.30` is administratively down.
5.  Generate/display the diagnosis.
6.  Show the remediation:

``` text
configure terminal
interface GigabitEthernet0/0.30
no shutdown
```

7.  Ask the operator to approve, edit, or reject the proposed fix.
8.  Save the decision to the audit log.

------------------------------------------------------------------------

## 8. System Architecture

The MVP uses four simple logical layers:

``` text
DATA TIER
   ↓
DIAGNOSTIC CORE
   ↓
HUMAN-IN-THE-LOOP GATE
   ↓
AUDIT & LOGGING
```

### Data Tier

Stores:

-   Diagnostic cases
-   System configuration

### Diagnostic Core

Contains:

-   Rule checker
-   Diagnostic orchestration
-   Prompt generation
-   JSON parsing

### HITL Gate

Provides:

-   Diagnosis display
-   Evidence display
-   Command review
-   Approve
-   Edit
-   Reject

### Audit & Logging

Stores:

-   Decisions
-   Overrides
-   Agreement/accuracy information
-   Edge cases

------------------------------------------------------------------------

## 9. Project Structure

The MVP should use the following simple structure:

``` text
netsage-ai/
│
├── data/
│   └── cases.csv
│
├── prompts/
│   └── diagnose_prompt.md
│
├── src/
│   ├── app.py
│   ├── checker.py
│   └── engine.py
│
├── docs/
│   └── model_audit_log.md
│
├── system_config.json
├── requirements.txt
├── README.md
└── .gitignore
```

### File Responsibilities

  File                           Responsibility
  ------------------------------ ----------------------------------------------------
  `data/cases.csv`               Stores diagnostic test cases
  `prompts/diagnose_prompt.md`   LLM diagnostic instructions
  `src/checker.py`               Deterministic network rules
  `src/engine.py`                Combines rules, prompt generation and JSON parsing
  `src/app.py`                   Streamlit web application
  `docs/model_audit_log.md`      Audit and human override records
  `system_config.json`           Basic thresholds/models/execution settings
  `requirements.txt`             Python dependencies
  `README.md`                    Setup and usage documentation

------------------------------------------------------------------------

## 10. User Flow

``` text
Start
  ↓
Open NetSage AI Dashboard
  ↓
Load cases.csv
  ↓
Select Case ID
  ↓
Display Symptom + Topology + CLI Output
  ↓
Run Deterministic Checker
  ↓
Known Error?
 ┌───────────────┐
 │               │
Yes             No
 │               │
 ↓               ↓
Flag Error     LLM Diagnosis
 └───────┬───────┘
         ↓
Structured Diagnostic Result
         ↓
Display Diagnosis + Evidence + Fix
         ↓
Human Decision
   ┌────┼────┐
   ↓    ↓    ↓
Approve Edit Reject
   ↓    ↓    ↓
   └────┼────┘
        ↓
   Audit Log
```

------------------------------------------------------------------------

## 11. UI Requirements

The Streamlit application should contain:

### Sidebar

-   Project name
-   Case selector
-   Optional case information

### Main Dashboard

Display:

-   Case ID
-   Symptom
-   Topology note
-   Severity
-   CLI output
-   Detected errors
-   Root cause
-   OSI layer
-   Confidence
-   Evidence
-   Next command
-   Fix steps

### Action Section

Buttons:

-   `Approve & Deploy Fix`
-   `Edit Commands`
-   `Reject`

### Audit Section

Show the result of the operator's decision.

------------------------------------------------------------------------

## 12. Technology Stack

  Category             Technology
  -------------------- ---------------------------
  Language             Python 3.10+
  UI                   Streamlit
  Data Processing      Pandas
  File Handling        pathlib
  Data Interchange     JSON
  Target Environment   Cisco IOS / Packet Tracer
  Documentation        Markdown
  Diagrams             Mermaid.js

The specific LLM provider/model is intentionally not fixed in this PRD
so the implementation can use the model available during development.

------------------------------------------------------------------------

## 13. Functional Requirements

### FR-01

The system shall load diagnostic cases from `cases.csv`.

### FR-02

The system shall allow the user to select a case.

### FR-03

The system shall display the selected case information and CLI output.

### FR-04

The system shall run deterministic rules against the CLI output.

### FR-05

The system shall identify known network errors using predefined rules.

### FR-06

The system shall generate a structured diagnostic result.

### FR-07

The system shall display evidence supporting the diagnosis.

### FR-08

The system shall display proposed remediation steps.

### FR-09

The system shall allow human approval, editing, or rejection.

### FR-10

The system shall record the operator decision.

------------------------------------------------------------------------

## 14. Non-Functional Requirements

### Simplicity

The application should remain easy to understand and maintain.

### Safety

The MVP must not automatically execute AI-generated commands against
real network devices.

### Reliability

Known network errors should be handled through deterministic rules
wherever possible.

### Usability

A user should be able to select a case and understand the diagnosis
without reading source code.

### Maintainability

Rules, prompts, data, UI, and audit logs should remain separated into
their respective files.

------------------------------------------------------------------------

## 15. MVP Success Criteria

The MVP is considered complete when:

-   [ ] The Streamlit application starts successfully.
-   [ ] The case dataset loads correctly.
-   [ ] A user can select a diagnostic case.
-   [ ] CLI output is displayed.
-   [ ] The deterministic checker detects known errors.
-   [ ] The diagnostic engine produces structured output.
-   [ ] Root cause and evidence are displayed.
-   [ ] Fix steps are displayed.
-   [ ] The user can approve, edit, or reject a fix.
-   [ ] The decision is recorded in the audit log.
-   [ ] At least one complete end-to-end case such as `NET-001` works
    successfully.
-   [ ] Multiple predefined cases can be tested.

------------------------------------------------------------------------

## 16. Development Approach

Build the project incrementally:

### Phase 1 --- Project Setup

Create the project structure and install dependencies.

### Phase 2 --- Dataset

Create/load the 30 structured diagnostic cases.

### Phase 3 --- Rule Engine

Implement deterministic checks for known network errors.

### Phase 4 --- Diagnostic Engine

Connect the rule checker with prompt generation and structured JSON
parsing.

### Phase 5 --- Streamlit UI

Build the case selection and diagnostic dashboard.

### Phase 6 --- HITL Workflow

Add Approve, Edit, and Reject actions.

### Phase 7 --- Audit Logging

Record operator decisions and overrides.

### Phase 8 --- Testing

Run all predefined cases and verify expected faults and outputs.

### Phase 9 --- Documentation

Update README and audit documentation.

------------------------------------------------------------------------

## 17. Testing Strategy

Testing should focus on the predefined cases rather than
production-scale infrastructure.

For each case, verify:

1.  Input loads correctly.
2.  Expected error is detected when a deterministic rule exists.
3.  Diagnosis is understandable.
4.  Evidence is relevant.
5.  Proposed fix is appropriate for the case.
6.  Structured JSON remains valid.
7.  HITL actions work.
8.  Audit information is recorded.

------------------------------------------------------------------------

## 18. Safety Boundary

NetSage AI is an **MVP diagnostic assistant**.

The system should:

-   Analyze provided network outputs.
-   Suggest possible fixes.
-   Show evidence.
-   Require human review.

The system should **not** independently execute configuration changes on
real routers or switches.

Any future real-device deployment would require additional security,
authentication, validation, rollback, monitoring, and infrastructure
work outside the MVP scope.

------------------------------------------------------------------------

## 19. Future Enhancements

These are intentionally postponed until after the MVP:

-   Live Cisco device integration
-   SSH-based diagnostics
-   Real network telemetry
-   Automatic configuration deployment
-   Rollback mechanisms
-   Authentication and role-based access
-   Database-backed audit history
-   Advanced network topology visualization
-   More diagnostic rules
-   More network protocols
-   Production cloud deployment
-   Advanced evaluation and monitoring

------------------------------------------------------------------------

## 20. Final MVP Definition

**NetSage AI MVP =**

> A Streamlit-based AI-assisted network diagnostic web application that
> analyzes predefined Cisco Packet Tracer/IOS troubleshooting cases
> using deterministic rules and LLM reasoning, presents structured
> diagnoses and remediation steps, requires human approval before
> accepting a fix, and records the decision in an audit log.

The priority is **a working, demonstrable prototype with a clean
architecture**, not production infrastructure.
