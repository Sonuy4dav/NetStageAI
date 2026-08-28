# NetStage AI Dataset

Phase 3 uses the uploaded `data/cases.csv` as the source of truth. The file is read-only for this project and is not generated, normalized, or rewritten by the application.

## Current coverage

- 30 troubleshooting cases
- Case IDs: `NET-001` through `NET-030`
- Cisco IOS and Packet Tracer-oriented scenarios
- Coverage includes DHCP, DNS, OSPF, ACL, NAT, VLANs, routing, wireless, IPv6, HSRP, VTP, DAI, port security, and CDP
- Each case contains a symptom, topology note, CLI/configuration evidence, expected fault, OSI layer, concept tag, and severity

## Dataset quality gate

Run this command from the project root:

```powershell
python -c "from pathlib import Path; from src.dataset import validate_dataset; errors = validate_dataset(Path('data/cases.csv')); print('dataset valid' if not errors else '\\n'.join(errors))"
```

The validator checks that the file loads, case IDs are unique, expected faults and OSI layers are present, and severity values are supported. It reports errors and never modifies the CSV.

## Coverage summary

```powershell
python -c "from pathlib import Path; from src.engine import DiagnosticEngine; from src.dataset import summarize_dataset; summary = summarize_dataset(DiagnosticEngine(Path('data/cases.csv')).load_cases()); print(summary)"
```

The current deterministic checker only implements the administratively-down interface pattern. The remaining cases are available for later rule implementation or LLM diagnosis.
