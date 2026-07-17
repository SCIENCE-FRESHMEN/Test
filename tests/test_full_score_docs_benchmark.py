from pathlib import Path

from arm_agent.extensions.benchmark import run_quantitative_benchmark
from arm_agent.extensions.doc_updater import update_literature_review_metadata
from tools.literature_search_online import literature_search_online


def test_benchmark_writes_report(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    result = run_quantitative_benchmark(str(target))
    assert result["summary"]["case_count"] == 20
    assert target.exists()


def test_doc_updater_inserts_search_metadata(tmp_path: Path) -> None:
    report = tmp_path / "review.md"
    report.write_text("# Review\n", encoding="utf-8")
    search = literature_search_online("brain extracellular")
    result = update_literature_review_metadata(search, str(report))
    assert result["status"] == "review_metadata_updated"
    assert "自动检索元数据" in report.read_text(encoding="utf-8")


def test_benchmark_no_fabricated_references(tmp_path: Path) -> None:
    result = run_quantitative_benchmark(str(tmp_path / "report.md"))
    assert result["summary"]["fabricated_reference_incidents"] == 0
