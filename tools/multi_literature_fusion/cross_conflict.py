from __future__ import annotations

from typing import Any

from arm_agent.p0_tools.conflict_detector import detect_claim_conflicts


def detect_cross_paper_conflicts(arms: list[dict[str, Any]]) -> dict[str, Any]:
    claims = []
    for arm in arms:
        claims.extend(arm.get("claims", []) or [])
    result = detect_claim_conflicts(claims)
    result["limitations_patch"] = [{"category": "reference", "text": "Detected cross-paper conflict candidates require manual review.", "provenance": "model_infer"}]
    return result
