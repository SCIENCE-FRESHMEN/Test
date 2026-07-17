from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class HumanReviewRequest(BaseModel):
    review_id: str
    reason: Literal["claim_conflict", "missing_reference", "medical_risk", "tool_failure"]
    status: Literal["pending", "approved", "rejected", "supplemented"] = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_infer: bool = True


class PaperTaskState(BaseModel):
    source_file: str
    status: Literal["pending", "running", "completed", "failed", "isolated"] = "pending"
    attempts: int = 0
    result: dict[str, Any] | None = None
    failure_report: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)


class GraphRunState(BaseModel):
    run_id: str
    paper_tasks: list[PaperTaskState]
    cursor: int = 0
    review_requests: list[HumanReviewRequest] = Field(default_factory=list)
    completed: bool = False
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GraphCheckpoint(BaseModel):
    checkpoint_id: str
    state: GraphRunState
    storage_path: str
    saved_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
