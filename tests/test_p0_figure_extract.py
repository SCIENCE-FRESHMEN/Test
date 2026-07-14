from pathlib import Path

from arm_agent.p0_tools import extract_figure_evidence


def test_figure_extract_reads_caption_text(tmp_path: Path) -> None:
    source = tmp_path / "paper.txt"
    source.write_text(
        "Results\n"
        "Figure 1. Extracellular space tracer distribution in the brain interstitial system shows regional variation across sampled tissue. "
        "The caption is source text and should be kept as paper_original evidence.\n",
        encoding="utf-8",
    )

    result = extract_figure_evidence(str(source))

    assert result["status"] == "figure_extract_success"
    assert len(result["figures"]) == 1
    assert result["figures"][0]["source_attribution"] == "paper_original"
    assert result["figures"][0]["evidence_type"] == "figure_caption"


def test_figure_extract_missing_file_returns_failure() -> None:
    result = extract_figure_evidence("fixtures/does_not_exist.txt")

    assert result["status"] == "figure_extract_failed"
    assert result["risks"][0]["review_required"] is True
