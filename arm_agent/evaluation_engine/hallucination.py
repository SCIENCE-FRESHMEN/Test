from __future__ import annotations

from typing import Any


def detect_claim_hallucinations(claims: list[dict[str, Any]], source_text: str) -> dict[str, Any]:
    source_norm = _norm(source_text)
    records = []
    for claim in claims:
        raw = str(claim.get("raw_text") or claim.get("text") or "")
        supported = _norm(raw) in source_norm
        attribution = claim.get("source_attribution", "paper_original")
        hallucination_risk = not supported and attribution != "model_infer"
        records.append({
            "claim_id": claim.get("claim_id"),
            "supported_by_source_text": supported,
            "source_attribution": attribution,
            "hallucination_risk": hallucination_risk,
            "review_required": hallucination_risk,
        })
    return {
        "hallucination_count": sum(1 for item in records if item["hallucination_risk"]),
        "records": records,
        "trace": [{"stage": "hallucination_detection", "claims": len(claims)}],
    }


def _norm(text: str) -> str:
    return " ".join(text.lower().split())
