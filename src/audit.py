"""Append-only audit logging for human diagnostic decisions."""

import json
import os
from pathlib import Path

from .models import AuditEvent
from .security import audit_path_is_allowed


def record_decision(
    log_path: Path,
    event: AuditEvent,
    project_root: Path | None = None,
) -> None:
    """Append one validated, complete audit event as a Markdown JSON block."""
    if project_root is not None and not audit_path_is_allowed(log_path, project_root):
        raise ValueError("audit log path must be the configured project audit file")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": event.timestamp,
        "case_id": event.case_id,
        "decision": event.decision,
        "diagnosis": event.diagnosis.as_dict(),
        "original_commands": [command.as_dict() for command in event.original_commands],
        "edited_commands": [command.as_dict() for command in event.edited_commands],
        "human_override": event.human_override,
        "error_information": event.error_information,
    }
    entry = "\n## Decision: " + event.timestamp + "\n\n```json\n"
    entry += json.dumps(payload, indent=2) + "\n```\n"
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(entry)
        log_file.flush()
        os.fsync(log_file.fileno())
