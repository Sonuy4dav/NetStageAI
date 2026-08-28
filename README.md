# NetStage AI

NetStage AI is a Streamlit prototype that diagnoses predefined Cisco IOS and
Packet Tracer troubleshooting cases. It combines deterministic checks with a
human review workflow and records approval, rejection, and command-edit
decisions.

The application is a read-only diagnostic demonstrator. It does not connect to
network devices or execute the commands it displays.

Live demo: https://netstageai-htxgv8tsayvsrtetxv2v7c.streamlit.app/

## Problem statement

Network troubleshooting often requires correlating CLI evidence with known
configuration faults and documenting the operator's decision. NetStage AI
provides a small, auditable workflow for predefined Cisco IOS and Packet Tracer
cases without changing a real device.

## Features

- 30 validated diagnostic cases loaded from CSV
- Deterministic Cisco rule engine with evidence, severity, confidence, and OSI layer
- Safe fallback behavior for unknown, incomplete, conflicting, or unavailable diagnoses
- Human-in-the-loop approval, rejection, and command editing
- Append-only Markdown audit records
- Secret redaction and bounded CLI input handling

## Architecture and technical approach

The Streamlit UI in `src/app.py` loads the dataset through `src/dataset.py`,
evaluates CLI evidence with `src/checker.py`, and orchestrates typed diagnoses
through `src/engine.py` and `src/models.py`. The repository-root `app.py` is the
Streamlit Cloud launcher and executes the packaged UI module with the correct
import path.

The rule engine is the primary diagnostic path. It matches specific known
patterns and returns supporting CLI evidence, proposed commands, severity,
confidence, and OSI layer. Multiple matches produce a conflict diagnosis with
no automatic fix. A no-match result is explicitly not proof that the network is
healthy.

The LLM layer is provider-neutral and currently disabled. `src/llm.py` builds a
sanitized, structured prompt and strictly validates JSON responses, while
`system_config.json` keeps deterministic-only mode enabled. No model API is
called by the deployed application.

Evidence is grounded in the selected case's sanitized CLI output and the
deterministic rule result. Proposed commands are display-only. The HITL flow
requires an explicit review confirmation before approval or rejection, and
records edits and decisions for auditability.

## Tech stack

Python 3.10+, Streamlit, pandas, CSV, JSON, pathlib, Markdown, and unittest.

## Requirements

- Python 3.10 or newer
- pip
- Windows PowerShell, macOS/Linux shell, or an equivalent terminal

## Setup

From the repository root (`D:\Net Stage Ai` in the supplied workspace), create
and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependency ranges:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run Streamlit

Start the application from the repository root:

```powershell
python -m streamlit run app.py
```

Streamlit prints a local URL, normally `http://localhost:8501`. Open it in a
browser, select a case, and choose **Run Diagnosis**. Review the evidence and
proposed commands before using **Edit Commands**, **Approve Fix**, or **Reject
Fix**. Decisions are appended to `docs/model_audit_log.md`.

To run without opening a browser:

```powershell
python -m streamlit run app.py --server.headless true --server.port 8501
```

## Deploy on Streamlit Community Cloud

1. Create a public or private GitHub repository and push this project from its
	root directory.
2. In Streamlit Community Cloud, choose **Create app**, select the repository
	and branch, and set the main file to `app.py`.
3. Use Python 3.10 or newer in the app's advanced settings. Streamlit Cloud
	installs the packages from `requirements.txt` automatically.
4. Deploy with `system_config.json` left in deterministic-only mode. The
	current app has no active LLM provider and does not require an API key.

The app can create `docs/model_audit_log.md` while it is running, but
Streamlit Community Cloud storage is ephemeral. Audit entries are not a
durable shared record and are intentionally excluded from GitHub. Use a
database or another external persistence service before relying on audit
history in production.

If a future provider integration needs a credential, add it in the Streamlit
Cloud app settings under **Secrets** and read it at runtime. Never commit
`.env`, `.streamlit/secrets.toml`, API keys, passwords, device configurations,
or generated audit logs.

## Publish safely to GitHub

From the repository root, review the files that will be staged before the
first push:

```powershell
git init
git add .
git status --short
git diff --cached --check
```

Confirm that no `.env` file, Streamlit secrets file, ZIP archive, audit log,
private key, or credential is listed. Create the GitHub repository first, then
add its HTTPS or SSH URL as `origin`, commit, and push the chosen branch.

## Configuration and environment variables

`system_config.json` controls the current prototype configuration:

| Setting | Current meaning |
| --- | --- |
| `deterministic_only` | When `true` (the default), cases marked `requires_llm` use a safe deterministic fallback. |
| `llm_enabled` | Reserved metadata; the current Streamlit entry point does not create an LLM provider. |
| `llm_timeout_seconds` | Intended provider timeout value; provider integration must enforce it. |
| `max_cli_output_chars` | Documented input limit; source validation currently enforces 12,000 characters. |
| `audit_log_path` | Intended audit location; the app writes to `docs/model_audit_log.md`. |

The optional environment variable `NETSTAGE_LLM_API_KEY` is read by
`src/security.py` through `get_provider_api_key()`. It is deliberately not
stored in project files and is not sent anywhere by the current application.
Set it only when implementing and wiring a trusted provider adapter:

```powershell
$env:NETSTAGE_LLM_API_KEY = "your-provider-key"
```

Do not commit keys, passwords, device configurations, or unsanitized command
output. The current app sanitizes common secrets before displaying CLI output
or constructing an LLM prompt.

## Add a case

Cases live in `data/cases.csv`. Required columns are:

```text
case_id,symptom,topology_note,show_outputs,expected_fault,osi_layer,concept_tag,severity
```

Optional columns are `expected_osi_layer`, `expected_evidence`,
`expected_commands`, and `requires_llm`. The loader also accepts `osi_layer` as
the source for the OSI layer. `expected_evidence` and `expected_commands` use
semicolon-separated values. `requires_llm` accepts `true`, `false`, `1`, `0`,
`yes`, or `no`.

Add one CSV row, quote any field containing commas or line breaks, and use a
unique case ID. For example:

```csv
NET-031,Host cannot reach the gateway,PC on access port Fa0/3,interface GigabitEthernet0/1 is administratively down line protocol is down,Interface administratively down,Layer 3,Interface,High
```

Run the dataset tests after editing. The application validates required fields,
duplicate IDs, severity values, and non-empty diagnostic input at startup.

## Add a deterministic rule

Rules are registered in `src/checker.py` in the `RULES` tuple. A rule needs a
unique ID, message, matcher, proposed commands, OSI layer, confidence, and
severity. For a simple phrase-based check:

```python
RuleDefinition(
	 "ARP_INSPECTION_DISABLED",
	 "Dynamic ARP Inspection is disabled on the access port.",
	 _contains("ip arp inspection disabled", "access port"),
	 ["interface <affected-interface>", "ip arp inspection vlan <vlan-id>"],
	 "Layer 2",
	 0.95,
	 "HIGH",
),
```

For structured output, add the rule to `RULES`, add a focused test in
`tests/test_source_workflow.py`, and include matching evidence in a case. Keep
matchers specific enough to avoid false positives. `evaluate_show_output()`
returns `ERRORS_DETECTED` with findings or `NO_KNOWN_ERROR` when nothing
matches. Multiple matches are treated as a conflict by the diagnostic engine,
so no automatic fix is produced.

## Configure an LLM

The current repository provides provider-neutral prompt construction and strict
JSON parsing in `src/llm.py`; it does not include an OpenAI, Azure, or other
provider client. LLM-enabled operation therefore requires a developer to:

1. Implement a provider callable that accepts the prompt from
	`build_diagnosis_prompt()` and returns JSON matching `DIAGNOSIS_SCHEMA`.
2. Read credentials from `NETSTAGE_LLM_API_KEY` using the existing security
	helper.
3. Pass that callable as `llm_diagnoser` when constructing `DiagnosticEngine`.
4. Set `deterministic_only` to `false` only after testing timeout, connection,
	invalid-JSON, and human-review behavior.

Until those steps are completed, leave `deterministic_only` set to `true`.
Failures, unavailable providers, invalid JSON, and timeouts intentionally fall
back to a zero-confidence diagnosis requiring human investigation.

## Safety limitations

- This prototype never SSHs, Telnets, or connects to a real device.
- Proposed commands are displayed for review and are never executed by the app.
- Approval records a human decision; it is not deployment.
- CLI input is limited to 12,000 characters and common credentials are redacted.
- Treat uploaded CLI output and model output as untrusted data.
- Deterministic rules only recognize known patterns; `NO_KNOWN_ERROR` is not
  proof that a network is healthy.
- A model diagnosis can be wrong or incomplete. Verify evidence and commands
  against the lab topology and device documentation before applying anything.

## Future scope

- Add a tested provider adapter behind the existing LLM interface.
- Replace local Markdown audit storage with durable external persistence.
- Support controlled user-supplied cases and richer evidence review.
- Add broader rule coverage and automated quality reporting.

## Testing

Run the complete regression suite from the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests cover CSV loading and quality checks, all 30 bundled cases, rule
matching and false-positive protection, diagnosis fallbacks, LLM JSON parsing,
security redaction, and audit logging. A successful run ends with `OK`.

## Example diagnostic workflow

1. Start Streamlit and open the local URL.
2. Select `NET-001`.
3. Confirm the symptom: PC1 cannot reach Server1 in VLAN 30.
4. Choose **Run Diagnosis**.
5. The deterministic checker matches `INTERFACE_ADMIN_DOWN` and reports the
	affected sub-interface as administratively down.
6. Review the evidence, the next command (`show running-config interface
	GigabitEthernet0/0.10`), and the proposed `no shutdown` fix.
7. Select **Approve Fix** or **Edit Commands**, tick the review confirmation,
	and confirm the decision.
8. Open `docs/model_audit_log.md` to verify that the decision and diagnosis were
	recorded. No network change occurs.

## Project structure

```text
data/cases.csv             Bundled diagnostic cases
docs/                      Audit log and project documentation
prompts/                   Prompt assets
src/app.py                 Streamlit entry point
src/checker.py             Deterministic rules
src/engine.py              Diagnosis orchestration
src/llm.py                 Prompt construction and response parsing
tests/                     Automated regression tests
system_config.json         Prototype configuration
requirements.txt           Python dependency ranges
```
