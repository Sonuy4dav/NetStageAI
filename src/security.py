"""Safety boundaries for untrusted CLI input and prototype operation."""

import os
import re
from pathlib import Path


MAX_CLI_OUTPUT_CHARS = 12_000
AUDIT_LOG_RELATIVE_PATH = Path("docs") / "model_audit_log.md"

_SECRET_PATTERNS = (
    re.compile(r"(?im)(\b(?:password|passwd|secret|community|token|api[_ -]?key)\s*[=:]\s*)[^\s;]+"),
    re.compile(r"(?im)(\benable\s+secret\s+)[^\s;]+"),
    re.compile(r"(?im)(\bradius-server\s+host\s+\S+\s+key\s+)[^\s;]+"),
)


def validate_cli_output(value: object) -> str:
    """Validate and return CLI text within the prototype input limit."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("CLI output must be a non-empty string")
    if len(value) > MAX_CLI_OUTPUT_CHARS:
        raise ValueError(
            f"CLI output exceeds the {MAX_CLI_OUTPUT_CHARS}-character limit"
        )
    return value


def sanitize_cli_output(value: str) -> str:
    """Mask common credentials before CLI text is displayed or sent to an LLM."""
    sanitized = value
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
    return sanitized


def audit_path_is_allowed(log_path: Path, project_root: Path) -> bool:
    """Return whether a log path is exactly the configured project audit file."""
    expected = (project_root / AUDIT_LOG_RELATIVE_PATH).resolve()
    return log_path.resolve() == expected


def get_provider_api_key(environment_variable: str = "NETSTAGE_LLM_API_KEY") -> str | None:
    """Read a provider key from the process environment, never from project files."""
    return os.getenv(environment_variable)
