from arm_agent.extensions.handoff import plan_handoff
from arm_agent.extensions.scheduler import schedule_tasks


def test_handoff_figure_parse() -> None:
    result = plan_handoff("figure_parse", {"figures": [1, 2]})
    assert result["handoff"]["to_agent"] == "FigureEvidenceAgent"
    assert result["handoff"]["model_infer"] is True


def test_handoff_conflict_check() -> None:
    result = plan_handoff("conflict_check", {"claims": [1]})
    assert result["handoff"]["to_agent"] == "ConflictReviewAgent"


def test_scheduler_orders_light_before_heavy_and_online() -> None:
    result = schedule_tasks(["online_search", "literature_extract", "figure_parse"])
    assert [item["priority"] for item in result] == ["light", "heavy", "online"]
