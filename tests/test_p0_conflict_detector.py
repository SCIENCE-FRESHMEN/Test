from arm_agent.p0_tools import detect_claim_conflicts


def test_conflict_detector_flags_cross_paper_opposite_polarity() -> None:
    claims = [
        {
            "claim_id": "A",
            "source_file": "paper_a.txt",
            "source_location": "Results paragraph 1",
            "raw_text": "The extracellular brain clearance pathway shows increased amyloid clearance.",
        },
        {
            "claim_id": "B",
            "source_file": "paper_b.txt",
            "source_location": "Results paragraph 2",
            "raw_text": "The extracellular brain clearance pathway does not show amyloid clearance.",
        },
    ]

    result = detect_claim_conflicts(claims)

    assert result["status"] == "conflict_review_required"
    assert result["conflict_pairs"][0]["review_required"] is True


def test_conflict_detector_ignores_same_paper_pairs() -> None:
    claims = [
        {"source_file": "paper.txt", "raw_text": "The extracellular brain pathway shows amyloid clearance."},
        {"source_file": "paper.txt", "raw_text": "The extracellular brain pathway does not show amyloid clearance."},
    ]

    result = detect_claim_conflicts(claims)

    assert result["status"] == "no_conflict_detected"
