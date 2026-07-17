from arm_agent.extensions.evidence_trust import annotate_arm_evidence_trust, compare_conflict_trust, score_evidence_trust


def test_evidence_trust_clinical_review() -> None:
    score = score_evidence_trust({"quote": "clinical systematic review in patients"})
    assert score["trust_level"] == "clinical_review"
    assert score["score"] > 0.8


def test_evidence_trust_animal() -> None:
    score = score_evidence_trust({"quote": "mouse in vivo brain extracellular experiment"})
    assert score["trust_level"] == "animal_experiment"


def test_conflict_trust_comparison() -> None:
    result = compare_conflict_trust({"conflict_id": "CON-1", "claim_a": {"raw_text": "clinical patient review"}, "claim_b": {"raw_text": "model inference"}})
    assert result["conflict_score"] > 0
    assert result["review_required"] is True


def test_annotate_arm_evidence_trust() -> None:
    result = annotate_arm_evidence_trust({"evidence": [{"evidence_id": "E-1", "quote": "cell culture in vitro"}]})
    assert result["evidence_trust"][0]["trust_level"] == "in_vitro_cell"
