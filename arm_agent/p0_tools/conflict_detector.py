from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConflictPair(BaseModel):
    conflict_id: str
    claim_a: dict[str, Any]
    claim_b: dict[str, Any]
    shared_terms: list[str]
    risk_level: Literal["low", "medium", "high"]
    reason: str
    review_required: bool = True


class ConflictDetectionResult(BaseModel):
    status: Literal["no_conflict_detected", "conflict_review_required"]
    conflict_pairs: list[ConflictPair] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


NEGATIVE_TERMS = {
    "not",
    "no",
    "without",
    "failed",
    "does not",
    "did not",
    "absence",
    "lack",
    "lacks",
    "reduced",
    "decreased",
}
POSITIVE_TERMS = {
    "show",
    "shows",
    "showed",
    "demonstrated",
    "indicates",
    "increased",
    "associated",
    "enhanced",
    "improved",
}
DOMAIN_TERMS = {
    "ecs",
    "extracellular",
    "glymphatic",
    "interstitial",
    "amyloid",
    "alzheimer",
    "diffusion",
    "clearance",
    "brain",
    "dementia",
}


def detect_claim_conflicts(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag conservative cross-paper conflict candidates for human review."""
    trace = [{"stage": "conflict_detection_start", "claim_count": len(claims)}]
    pairs: list[ConflictPair] = []
    for claim_a, claim_b in combinations(claims, 2):
        if claim_a.get("source_file") == claim_b.get("source_file"):
            continue
        shared = sorted(_domain_terms(_claim_text(claim_a)) & _domain_terms(_claim_text(claim_b)))
        if not shared:
            continue
        polarity_a = _polarity(_claim_text(claim_a))
        polarity_b = _polarity(_claim_text(claim_b))
        if polarity_a * polarity_b < 0:
            risk = "high" if len(shared) >= 2 else "medium"
            pairs.append(
                ConflictPair(
                    conflict_id=f"CON-{len(pairs) + 1:03d}",
                    claim_a=_compact_claim(claim_a),
                    claim_b=_compact_claim(claim_b),
                    shared_terms=shared,
                    risk_level=risk,
                    reason="Opposite lexical polarity detected on shared neuroscience/ECS terms; manual review required.",
                )
            )
        if len(pairs) >= 25:
            break
    trace.append({"stage": "conflict_detection_completed", "conflict_count": len(pairs)})
    return ConflictDetectionResult(
        status="conflict_review_required" if pairs else "no_conflict_detected",
        conflict_pairs=pairs,
        trace=trace,
    ).model_dump()


def _claim_text(claim: dict[str, Any]) -> str:
    return str(claim.get("raw_text") or claim.get("text") or "")


def _domain_terms(text: str) -> set[str]:
    low = text.lower()
    return {term for term in DOMAIN_TERMS if term in low}


def _polarity(text: str) -> int:
    low = text.lower()
    negative = any(term in low for term in NEGATIVE_TERMS)
    positive = any(term in low for term in POSITIVE_TERMS) or bool(re.search(r"\b(increase|enhance|improve|associate)", low))
    if negative and not positive:
        return -1
    if positive and not negative:
        return 1
    if negative and positive:
        return -1
    return 0


def _compact_claim(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id"),
        "source_file": claim.get("source_file"),
        "source_location": claim.get("source_location") or claim.get("locator"),
        "raw_text": _claim_text(claim),
    }
