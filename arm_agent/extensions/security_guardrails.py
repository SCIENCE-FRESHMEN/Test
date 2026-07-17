from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class SecurityCheckResult(BaseModel):
    status: Literal["security_passed", "security_blocked"]
    risks: list[dict[str, Any]] = Field(default_factory=list)
    failure_report: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)


INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"bypass\s+(?:guardrails|safety)",
]
CLINICAL_PATTERNS = [
    r"diagnos(?:e|is)",
    r"prescrib(?:e|ing)",
    r"dosage",
    r"treatment\s+plan",
    r"clinical\s+decision",
    r"用药",
    r"处方",
    r"诊断",
    r"预后",
    r"治疗建议",
]


def check_input_safety(text: str, source: str = "user_input") -> dict[str, Any]:
    trace = [{"stage": "security_check_start", "source": source}]
    risks: list[dict[str, Any]] = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.I):
            risks.append({"code": "prompt_injection_detected", "pattern": pattern, "severity": "high", "review_required": True})
    for pattern in CLINICAL_PATTERNS:
        if re.search(pattern, text, re.I):
            risks.append({"code": "clinical_instruction_blocked", "pattern": pattern, "severity": "high", "review_required": True})
    trace.append({"stage": "security_check_completed", "risk_count": len(risks)})
    if risks:
        return SecurityCheckResult(
            status="security_blocked",
            risks=risks,
            failure_report={
                "status": "blocked",
                "reason": "security_guardrail_triggered",
                "no_success_arm_generated": True,
                "missing_or_risky_items": risks,
                "manual_review_recommendation": "Remove prompt-injection or clinical decision instructions; submit research-literature content only.",
            },
            trace=trace,
        ).model_dump()
    return SecurityCheckResult(status="security_passed", trace=trace).model_dump()
