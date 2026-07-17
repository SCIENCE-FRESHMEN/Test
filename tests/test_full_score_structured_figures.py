from arm_agent.extensions.structured_figures import parse_structured_figures


def test_structured_figure_panels() -> None:
    result = parse_structured_figures({"figures": [{"figure_id": "Figure 1", "caption": "(A) Extracellular tracer spread increased in mouse cortex. (B) Glymphatic clearance differed across sleep states.", "source_file": "x.txt", "locator": "Figure 1 caption", "evidence_type": "figure_caption"}]})
    assert len(result["panels"]) == 2


def test_structured_table_rows() -> None:
    result = parse_structured_figures({"figures": [{"figure_id": "Table 1", "caption": "group | control | value | 1.0", "source_file": "x.txt", "locator": "Table 1 caption", "evidence_type": "table_caption"}]})
    assert result["tables"][0]["rows"]


def test_structured_table_review_when_no_rows() -> None:
    result = parse_structured_figures({"figures": [{"figure_id": "Table 2", "caption": "Plain caption without cells", "source_file": "x.txt", "locator": "Table 2 caption", "evidence_type": "table_caption"}]})
    assert result["tables"][0]["review_required"] is True
