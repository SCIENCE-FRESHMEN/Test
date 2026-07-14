from arm_agent.pipeline import PaperToARMOrchestrator


def test_success_case_generates_full_arm() -> None:
    result = PaperToARMOrchestrator(output_dir="outputs/test").run(["brain_ECS_review.txt"], export_yaml=False)
    arm = result.full_arm
    assert arm.metadata.processing_status == "success"
    assert arm.metadata.ecs_related is True
    assert len(arm.claims) >= 5
    assert all(claim.evidence_ids for claim in arm.claims)
    assert all(claim.raw_text == claim.support_evidence_snippet[0] for claim in arm.claims)
    assert all(claim.source_attribution == "paper_original" for claim in arm.claims)
    assert arm.provenance["reference_validation"]["status"] in {"reference_valid", "reference_invalid"}
    assert "identifier_invalid" in arm.provenance["reference_validation"]["summary"]
    assert any(step.can_dry_run for step in arm.runbook)


def test_failure_case_blocks_incomplete_input() -> None:
    result = PaperToARMOrchestrator(output_dir="outputs/test").run(["fixtures/incomplete_paper.txt"], export_yaml=False)
    arm = result.full_arm
    assert arm["metadata"]["processing_status"] == "failed"
    assert arm["failure_report"]["no_success_arm_generated"] is True
    codes = {risk["code"] for risk in arm["failure_report"]["missing_or_risky_items"]}
    assert "ecs_information_missing" in codes
    assert "missing_figures_tables" in codes


def test_full_papers_batch_generates_arm() -> None:
    from pathlib import Path

    papers = sorted(str(path) for path in Path("fixtures/full_papers").glob("*.pdf"))[:5]
    assert len(papers) == 5
    result = PaperToARMOrchestrator(output_dir="outputs/test").run(papers, export_yaml=False)
    arm = result.full_arm
    assert arm.metadata.processing_status == "success"
    assert len(arm.provenance["source_files"]) == 5
    assert len(arm.claims) >= 5
    assert all(claim.raw_text == claim.support_evidence_snippet[0] for claim in arm.claims)
    assert arm.provenance["reference_validation"]["status"] in {"reference_valid", "reference_invalid"}
    assert "domain_mismatch_or_unclear" in arm.provenance["reference_validation"]["summary"]
    assert len(result.trace_record.tool_calls) == 6
