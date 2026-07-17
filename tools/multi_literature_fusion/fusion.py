from __future__ import annotations

from typing import Any

from arm_agent.extensions.evidence_trust import compare_conflict_trust
from arm_agent.p0_tools.conflict_detector import detect_claim_conflicts


def fuse_arm_assets(arms: list[dict[str, Any]]) -> dict[str, Any]:
    claims = []
    evidence = []
    source_files = []
    seen = set()
    for arm in arms:
        source_files.extend(arm.get("provenance", {}).get("source_files", []) or [])
        for claim in arm.get("claims", []) or []:
            text = claim.get("raw_text") or claim.get("text")
            if text in seen:
                continue
            seen.add(text)
            claims.append(claim)
        evidence.extend(arm.get("evidence", []) or [])
    conflict = detect_claim_conflicts(claims)
    trust = [compare_conflict_trust(pair) for pair in conflict.get("conflict_pairs", [])]
    return {
        "status": "fusion_success",
        "claims": claims,
        "evidence": evidence,
        "provenance": {
            "source_files": sorted(set(source_files)),
            "fusion_policy": "dedupe_by_raw_text_and_preserve_source_evidence",
            "conflict_detection": conflict,
            "conflict_trust": trust,
            "model_infer": True,
        },
        "limitations_patch": [{"category": "multi_literature_conflict", "text": "Cross-paper conflicts require manual review.", "provenance": "model_infer"}],
    }
