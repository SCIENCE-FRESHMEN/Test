from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TrustLevel = Literal["clinical_review", "animal_experiment", "in_vitro_cell", "model_infer"]


class EvidenceTrustScore(BaseModel):
    evidence_id: str | None = None
    trust_level: TrustLevel
    score: float
    rationale: str
    model_infer: bool = True


class ConflictTrustComparison(BaseModel):
    conflict_id: str
    conflict_type: Literal["paper_original_conflict", "model_infer_conflict", "source_mismatch"]
    claim_a_score: EvidenceTrustScore
    claim_b_score: EvidenceTrustScore
    conflict_score: float
    review_required: bool = True
    trace: list[dict[str, Any]] = Field(default_factory=list)


WEIGHTS: dict[TrustLevel, float] = {
    "clinical_review": 0.9,
    "animal_experiment": 0.7,
    "in_vitro_cell": 0.5,
    "model_infer": 0.25,
}


def score_evidence_trust(evidence_or_claim: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(evidence_or_claim.get(key, "")) for key in ["quote", "raw_text", "text", "section", "locator"]).lower()
    level: TrustLevel = "model_infer"
    rationale = "default_model_or_unclear_evidence"
    if any(token in text for token in ["clinical", "patient", "meta-analysis", "systematic review"]):
        level = "clinical_review"
        rationale = "clinical_or_review_signal_detected"
    elif any(token in text for token in ["mouse", "mice", "rat", "animal", "in vivo"]):
        level = "animal_experiment"
        rationale = "animal_or_in_vivo_signal_detected"
    elif any(token in text for token in ["cell", "culture", "in vitro", "astrocyte", "neuron"]):
        level = "in_vitro_cell"
        rationale = "cell_or_in_vitro_signal_detected"
    return EvidenceTrustScore(
        evidence_id=evidence_or_claim.get("evidence_id"),
        trust_level=level,
        score=WEIGHTS[level],
        rationale=rationale,
    ).model_dump()


def classify_conflict(conflict_pair: dict[str, Any]) -> str:
    a = conflict_pair.get("claim_a", {})
    b = conflict_pair.get("claim_b", {})
    if a.get("source_attribution") == "model_infer" or b.get("source_attribution") == "model_infer":
        return "model_infer_conflict"
    if a.get("source_file") != b.get("source_file"):
        return "source_mismatch"
    return "paper_original_conflict"


def compare_conflict_trust(conflict_pair: dict[str, Any]) -> dict[str, Any]:
    score_a = EvidenceTrustScore(**score_evidence_trust(conflict_pair.get("claim_a", {})))
    score_b = EvidenceTrustScore(**score_evidence_trust(conflict_pair.get("claim_b", {})))
    conflict_score = round(abs(score_a.score - score_b.score), 3)
    conflict_id = str(conflict_pair.get("conflict_id") or "CON-EXT")
    return ConflictTrustComparison(
        conflict_id=conflict_id,
        conflict_type=classify_conflict(conflict_pair),  # type: ignore[arg-type]
        claim_a_score=score_a,
        claim_b_score=score_b,
        conflict_score=conflict_score,
        trace=[{"stage": "conflict_trust_scored", "conflict_id": conflict_id, "conflict_score": conflict_score}],
    ).model_dump()


def annotate_arm_evidence_trust(full_arm: dict[str, Any]) -> dict[str, Any]:
    annotated = []
    for evidence in full_arm.get("evidence", []) or []:
        enriched = dict(evidence)
        trust = score_evidence_trust(evidence)
        enriched["trust_level"] = trust["trust_level"]
        enriched["trust_score"] = trust["score"]
        enriched["conflict_score"] = None
        annotated.append(enriched)
    return {"evidence_trust": annotated, "model_infer": True, "trace": [{"stage": "arm_evidence_trust_annotated", "count": len(annotated)}]}
