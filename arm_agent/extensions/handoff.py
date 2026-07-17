from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HandoffRecord(BaseModel):
    task_id: str
    task_type: Literal["figure_parse", "conflict_check", "online_search", "security_review"]
    from_agent: str = "manager"
    to_agent: str
    reason: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    status: Literal["assigned", "completed", "review_required"] = "assigned"
    model_infer: bool = True


def plan_handoff(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    targets = {
        "figure_parse": "FigureEvidenceAgent",
        "conflict_check": "ConflictReviewAgent",
        "online_search": "LiteratureSearchAgent",
        "security_review": "SafetyGuardrailAgent",
    }
    reason = "specialized_subagent_required_for_auditability"
    record = HandoffRecord(
        task_id=f"handoff-{task_type}",
        task_type=task_type,  # type: ignore[arg-type]
        to_agent=targets.get(task_type, "ReviewAgent"),
        reason=reason,
        input_summary={"keys": sorted(payload.keys()), "item_count": _count_items(payload)},
    )
    return {"handoff": record.model_dump(), "trace": [{"stage": "agent_handoff_planned", "task_type": task_type, "to_agent": record.to_agent}]}


def _count_items(payload: dict[str, Any]) -> int:
    total = 0
    for value in payload.values():
        if isinstance(value, list):
            total += len(value)
    return total
