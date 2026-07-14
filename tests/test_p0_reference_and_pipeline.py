from arm_agent.pipeline import PaperToARMOrchestrator
from arm_agent.tools import reference_validator


def test_reference_validator_marks_missing_identifier() -> None:
    result = reference_validator(
        [
            {
                "reference_text": "Smith J. Brain extracellular space study. Journal of Neuroscience. 2024.",
                "title": "Brain extracellular space study",
            }
        ]
    )

    assert result["status"] == "reference_invalid"
    assert result["summary"]["identifier_invalid"] == 1


def test_pipeline_writes_p0_results_to_provenance() -> None:
    result = PaperToARMOrchestrator(output_dir="outputs/test").run(["brain_ECS_review.txt"], export_yaml=False)
    provenance = result.full_arm.provenance

    assert "figure_extraction" in provenance
    assert "conflict_detection" in provenance
    assert "dry_run_result" in provenance
    assert "evaluation_result" in provenance
    assert "p0_trace_summary" in provenance
