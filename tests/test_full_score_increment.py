from schemas.arm_increment import merge_arm_increment


def _arm(claim_text: str, evidence_id: str) -> dict:
    return {
        "metadata": {"arm_id": "arm-a"},
        "claims": [{"claim_id": evidence_id.replace("E", "C"), "raw_text": claim_text, "evidence_ids": [evidence_id]}],
        "evidence": [{"evidence_id": evidence_id, "source_file": "paper.txt", "locator": "p1", "quote": claim_text}],
        "provenance": {"source_files": ["paper.txt"]},
    }


def test_increment_merge_adds_unique_claim() -> None:
    result = merge_arm_increment(_arm("A", "E-001"), _arm("B", "E-002"), "batch-1")
    assert result["status"] == "increment_merge_success"
    assert len(result["merged_arm"]["claims"]) == 2
    assert result["increment_record"]["claims_added"] == 1


def test_increment_merge_deduplicates_claim() -> None:
    result = merge_arm_increment(_arm("A", "E-001"), _arm("A", "E-002"), "batch-2")
    assert len(result["merged_arm"]["claims"]) == 1
    assert result["increment_record"]["duplicate_claims"] == 1


def test_increment_merge_writes_model_infer_policy() -> None:
    result = merge_arm_increment(_arm("A", "E-001"), _arm("B", "E-002"))
    assert result["merged_arm"]["provenance"]["model_infer"] is True
