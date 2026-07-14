from arm_agent.p0_tools import validate_arm_asset


def _valid_arm() -> dict:
    return {
        "metadata": {"processing_status": "success", "ecs_related": True},
        "claims": [
            {
                "claim_id": f"C-{idx:03d}",
                "raw_text": "Extracellular space is important.",
                "support_evidence_snippet": ["Extracellular space is important."],
                "evidence_ids": ["E-001"],
                "source_attribution": "paper_original",
            }
            for idx in range(1, 6)
        ],
        "evidence": [{"evidence_id": "E-001", "evidence_type": "text"}],
        "protocol": [{}],
        "runbook": [{"can_dry_run": True}],
        "eval_plan": [{}],
        "provenance": {},
        "limitations": [{"category": "medical_boundary"}],
        "artifacts": [],
    }


def test_arm_validator_accepts_complete_arm() -> None:
    result = validate_arm_asset(_valid_arm())

    assert result["validation_passed"] is True
    assert result["failed_checks"] == []


def test_arm_validator_rejects_model_infer_claim() -> None:
    arm = _valid_arm()
    arm["claims"][0]["source_attribution"] = "model_infer"

    result = validate_arm_asset(arm)

    assert result["validation_passed"] is False
    assert any(check["check_id"] == "ARM-004" for check in result["failed_checks"])
