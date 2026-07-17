from __future__ import annotations

from pathlib import Path
from typing import Any

from arm_agent.extensions.security_guardrails import check_input_safety

ALLOWED_SUFFIXES = {".pdf", ".txt"}


def validate_input_file(path: str, max_mb: int = 80) -> dict[str, Any]:
    file_path = Path(path)
    risks = []
    if file_path.suffix.lower() not in ALLOWED_SUFFIXES:
        risks.append({"code": "unsupported_file_type", "severity": "high", "review_required": True})
    if file_path.exists() and file_path.stat().st_size > max_mb * 1024 * 1024:
        risks.append({"code": "file_too_large", "severity": "high", "review_required": True})
    if not file_path.exists():
        risks.append({"code": "file_missing", "severity": "high", "review_required": True})
    return {"status": "input_file_blocked" if risks else "input_file_passed", "risks": risks, "trace": [{"stage": "input_file_validated", "path": path}]}


def validate_input_text(text: str, source: str = "user_input") -> dict[str, Any]:
    return check_input_safety(text, source=source)
