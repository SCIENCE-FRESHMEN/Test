from pathlib import Path

from arm_agent.p0_tools.figure_extract import extract_figure_evidence
from arm_agent.pipeline import PaperToARMOrchestrator
from arm_agent.tools import literature_extract
from tools.pdf_parser_tools.figure_images import extract_pdf_figure_images, match_images_to_captions


FULL_PAPERS_DIR = Path("fixtures/full_papers")


def _full_paper_pdfs() -> list[Path]:
    return sorted(FULL_PAPERS_DIR.glob("*.pdf"))


def _arm_dict(result) -> dict:
    return result.full_arm if isinstance(result.full_arm, dict) else result.full_arm.model_dump()


def test_full_paper_fixtures_extract_traceable_claims() -> None:
    pdfs = _full_paper_pdfs()
    assert pdfs, "fixtures/full_papers should contain PDF samples"

    for pdf in pdfs:
        extracted = literature_extract(str(pdf))
        assert len(extracted["candidate_claims"]) >= 5, pdf.name
        assert extracted["quality_flags"]["has_references"] is True


def test_full_paper_fixtures_single_pipeline_success_or_expected_block(tmp_path: Path) -> None:
    for index, pdf in enumerate(_full_paper_pdfs(), start=1):
        extracted = literature_extract(str(pdf))
        result = PaperToARMOrchestrator(output_dir=str(tmp_path / f"paper_{index}")).run([str(pdf)], export_yaml=False)
        arm = _arm_dict(result)
        if extracted["metadata"]["ecs_related"]:
            assert arm["metadata"]["processing_status"] == "success", pdf.name
            assert len(arm["claims"]) >= 5
            assert len(arm["evidence"]) >= 5
        else:
            assert arm["metadata"]["processing_status"] == "failed", pdf.name
            risks = [item["code"] for item in arm["failure_report"]["missing_or_risky_items"]]
            assert "ecs_information_missing" in risks


def test_full_paper_fixtures_batch_pipeline_success(tmp_path: Path) -> None:
    ecs_batch = [str(path) for path in _full_paper_pdfs() if literature_extract(str(path))["metadata"]["ecs_related"]][:5]
    assert len(ecs_batch) == 5
    result = PaperToARMOrchestrator(output_dir=str(tmp_path)).run(ecs_batch, export_yaml=False)
    arm = _arm_dict(result)
    assert arm["metadata"]["processing_status"] == "success"
    assert len(arm["provenance"]["source_files"]) == 5
    assert len(arm["claims"]) >= 5


def test_nanoscopic_pdf_extracts_real_figure_regions() -> None:
    pdf = FULL_PAPERS_DIR / "Nanoscopic Mapping of the Extracellular Space in Amyloid Plaque-rich Cortex.pdf"
    figures = extract_figure_evidence(str(pdf))["figures"]
    figure_ids = {figure["figure_id"] for figure in figures}
    assert {"Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Figure 6", "Figure 7"} <= figure_ids
    assert not any("Check for updates" in figure["caption"] for figure in figures)

    images = extract_pdf_figure_images(str(pdf), captions=figures)
    rows = match_images_to_captions(images["images"], figures)
    assert images["status"] == "figure_image_success"
    assert sum(1 for row in rows if row.get("image")) >= 7
    assert all(
        (row.get("image") or {}).get("extraction_method") == "caption_above_region"
        for row in rows
        if row.get("image")
    )
