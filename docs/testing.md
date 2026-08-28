# Phase 12 Testing

The project uses focused `unittest` coverage for the rule engine, data contracts, diagnostic engine, LLM parser, audit writer, and security boundaries.

## Run automated tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## Automated coverage

- CSV loading and 30-case dataset validation
- Required-field and invalid-row validation
- Known deterministic rule detection
- Unknown and similar-but-valid-looking output handling
- False-positive regression coverage
- Typed diagnosis and JSON serialization
- Invalid LLM JSON and schema validation
- LLM timeout, API-error, and deterministic-only behavior
- Approval, edit, rejection, and audit record creation
- Secret redaction and CLI input limits
- Audit path restrictions
- Complete typed diagnosis for every predefined case

## Manual Streamlit test

Start the application with the Windows-compatible command:

```powershell
python -m streamlit run src/app.py
```

Open `http://localhost:8501` and verify:

1. The sidebar lists `NET-001` through `NET-030`.
2. Selecting a case displays its case ID, symptom, topology, severity, and sanitized CLI output.
3. `Run Diagnosis` displays detected errors and the complete diagnosis.
4. `Edit Commands` saves an `EDITED` audit record.
5. `Approve Fix` requires the review checkbox and creates an `APPROVED` record.
6. `Reject Fix` requires the review checkbox and creates a `REJECTED` record.
7. Switching cases clears the previous diagnosis and review state.
8. No Cisco command is executed; all commands are display-only text.

The uploaded `data/cases.csv` file is read-only and must not be changed by testing.