from pathlib import Path

from arm_agent.evaluation_engine import compute_claim_metrics, detect_claim_hallucinations, validate_reference_content
from arm_agent.langgraph_orchestrator import LangGraphEnhancedOrchestrator
from arm_agent.security_audit import ResourceLimiter, SecurityAuditLogger, validate_input_file, validate_input_text
from tools.multi_literature_fusion import detect_cross_paper_conflicts, fuse_arm_assets
from tools.pdf_parser_tools import bind_figures_to_claims, ocr_scanned_pdf_stub


def test_evaluation_engine_metrics_and_hallucination() -> None:
    metrics = compute_claim_metrics([{"raw_text": "A"}], [{"canonical_text": "A"}, {"canonical_text": "B"}])
    assert metrics["precision"] == 1.0
    hallucination = detect_claim_hallucinations([{"claim_id": "C1", "raw_text": "Missing", "source_attribution": "paper_original"}], "source text")
    assert hallucination["hallucination_count"] == 1


def test_reference_content_validation() -> None:
    result = validate_reference_content([{"title": "Brain ECS", "doi": "10.1/x"}], "Brain ECS appears here")
    assert result["fake_reference_risk_count"] == 0


def test_security_audit_logger_and_gateway(tmp_path: Path) -> None:
    file_path = tmp_path / "paper.txt"
    file_path.write_text("paper", encoding="utf-8")
    assert validate_input_file(str(file_path))["status"] == "input_file_passed"
    assert validate_input_text("diagnosis please")["status"] == "security_blocked"
    logger = SecurityAuditLogger(str(tmp_path))
    logger.record("stage", {"a": 1}, {"b": 2})
    assert logger.export()["event_count"] == 1


def test_resource_limiter() -> None:
    limiter = ResourceLimiter(single_file_quota=1, min_interval_seconds=0)
    assert limiter.acquire()["status"] == "acquired"
    assert limiter.acquire()["status"] == "rate_limited"


def test_pdf_binding_and_ocr_stub() -> None:
    result = bind_figures_to_claims([{"claim_id": "C1", "raw_text": "Figure 1 shows ECS"}], [{"figure_id": "Figure 1", "caption": "ECS caption", "locator": "Figure 1 caption"}])
    assert result["visual_evidence_links"]
    assert ocr_scanned_pdf_stub("scan.pdf")["status"] == "ocr_review_required"


def test_multi_literature_fusion_conflict() -> None:
    arms = [
        {"claims": [{"source_file": "a", "raw_text": "The extracellular brain clearance pathway shows increased amyloid clearance."}], "evidence": [], "provenance": {"source_files": ["a"]}},
        {"claims": [{"source_file": "b", "raw_text": "The extracellular brain clearance pathway does not show amyloid clearance."}], "evidence": [], "provenance": {"source_files": ["b"]}},
    ]
    fused = fuse_arm_assets(arms)
    assert fused["status"] == "fusion_success"
    assert detect_cross_paper_conflicts(arms)["status"] == "conflict_review_required"


def test_langgraph_checkpoint_isolated_failure(tmp_path: Path) -> None:
    orchestrator = LangGraphEnhancedOrchestrator(output_dir=str(tmp_path / "runs"), checkpoint_dir=str(tmp_path / "ckpt"))
    result = orchestrator.start([str(tmp_path / "missing.txt")], run_id="lg-test")
    assert result["status"] == "completed"
    assert result["state"]["paper_tasks"][0]["status"] in {"failed", "isolated"}
