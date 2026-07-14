from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    sequence: int
    tool_name: Literal["literature_extract", "reference_validator"]
    input: dict[str, Any]
    output: dict[str, Any]


class TraceEvent(BaseModel):
    sequence: int
    stage: str
    status: Literal["started", "completed", "blocked", "warning"]
    detail: dict[str, Any] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    run_id: str
    input: dict[str, Any]
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    events: list[TraceEvent] = Field(default_factory=list)
    extraction_records: list[dict[str, Any]] = Field(default_factory=list)
    validation_results: dict[str, Any] = Field(default_factory=dict)
    failure_risks: list[dict[str, Any]] = Field(default_factory=list)


class Metadata(BaseModel):
    arm_id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    pmid: str | None = None
    year: int | None = None
    publication_date: str | None = None
    journal: str | None = None
    article_type: str | None = None
    license: str | None = None
    source_file: str
    ecs_related: bool
    ecs_keywords: list[str] = Field(default_factory=list)
    processing_status: Literal["success", "failed"]


class Evidence(BaseModel):
    evidence_id: str
    claim_id: str | None = None
    source_file: str
    locator: str
    section: str
    paragraph_index: int | None = None
    figure_or_table: str | None = None
    quote: str
    evidence_type: Literal["text", "figure_caption", "table_caption", "model_infer"]
    provenance: Literal["source_text", "model_infer"] = "source_text"


class Claim(BaseModel):
    claim_id: str
    text: str
    raw_text: str
    claim_category: Literal["experimental_result", "review_summary", "research_hypothesis"]
    section: str
    locator: str
    source_location: str
    evidence_ids: list[str]
    support_evidence_snippet: list[str]
    conflict_evidence_snippet: list[str] = Field(default_factory=list)
    source_attribution: Literal["paper_original", "model_infer"] = "paper_original"
    evidence_incomplete: bool = False
    ecs_related: bool
    claim_type: Literal["finding", "definition", "method", "limitation", "model_infer"]
    provenance: Literal["source_text", "model_infer"] = "source_text"
    requires_human_review: bool = False


class ProtocolStep(BaseModel):
    step_id: str
    name: str
    description: str
    input_materials: list[str]
    method_source_locator: str
    expected_output: str
    automation_level: Literal["auto", "manual_review", "not_runnable"]
    provenance: Literal["source_text", "model_infer"] = "source_text"


class RunbookStep(BaseModel):
    step_id: str
    action: str
    input_files: list[str]
    dependent_tools: list[str]
    expected_output: str
    manual_review_required: bool
    can_dry_run: bool
    dry_run_command: str | None = None
    failure_conditions: list[str] = Field(default_factory=list)


class EvalMetric(BaseModel):
    metric_id: str
    name: str
    pass_condition: str
    evaluation_method: str


class Limitation(BaseModel):
    limitation_id: str
    text: str
    category: Literal[
        "animal_to_human",
        "sample",
        "data_availability",
        "method",
        "ecs_gap",
        "medical_boundary",
        "reference",
        "input_quality",
    ]
    ecs_related: bool
    provenance: Literal["source_text", "model_infer"]
    evidence_ids: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    artifact_id: str
    type: str
    path: str
    description: str


class ARM(BaseModel):
    metadata: Metadata
    claims: list[Claim]
    evidence: list[Evidence]
    protocol: list[ProtocolStep]
    runbook: list[RunbookStep]
    eval_plan: list[EvalMetric]
    provenance: dict[str, Any]
    limitations: list[Limitation]
    artifacts: list[Artifact]


class PipelineOutput(BaseModel):
    full_arm: Any
    trace_record: TraceRecord
