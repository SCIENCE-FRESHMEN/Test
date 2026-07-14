from pathlib import Path

from arm_agent.eval import dry_run_arm, evaluate_dry_run


def _arm_with_file(path: Path) -> dict:
    return {
        "metadata": {"processing_status": "success"},
        "claims": [
            {"claim_id": f"C-{idx:03d}", "raw_text": "A", "support_evidence_snippet": ["A"], "evidence_ids": ["E-001"]}
            for idx in range(1, 6)
        ],
        "evidence": [{"evidence_id": "E-001"}],
        "protocol": [{}],
        "runbook": [
            {
                "step_id": "R-001",
                "action": "Dry-run pipeline",
                "input_files": [str(path)],
                "expected_output": "ARM modules exist",
                "can_dry_run": True,
            }
        ],
        "eval_plan": [{}],
        "provenance": {},
        "limitations": [{}],
        "artifacts": [],
    }


def test_dry_run_allows_pre_export_empty_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "paper.txt"
    source.write_text("paper", encoding="utf-8")
    arm = _arm_with_file(source)

    result = dry_run_arm(arm)
    evaluation = evaluate_dry_run(arm, result)

    assert result["status"] == "dry_run_passed"
    assert result["summary"]["pre_export_artifacts_allowed"] is True
    assert evaluation["status"] == "eval_passed"
    assert evaluation["summary"]["score"] == 100.0


def test_dry_run_missing_input_file_fails(tmp_path: Path) -> None:
    arm = _arm_with_file(tmp_path / "missing.txt")

    result = dry_run_arm(arm)

    assert result["status"] == "dry_run_failed"
    assert "missing_input_file" in result["steps"][0]["errors"][0]
