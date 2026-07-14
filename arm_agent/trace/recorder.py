from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceStepRecord(BaseModel):
    step_id: str
    stage: str
    status: Literal["started", "completed", "warning", "failed"]
    timestamp_utc: str
    input_ref: dict[str, Any] = Field(default_factory=dict)
    output_ref: dict[str, Any] = Field(default_factory=dict)
    risks: list[dict[str, Any]] = Field(default_factory=list)


class ClaimTraceRecord(BaseModel):
    claim_id: str
    source_file: str
    source_location: str
    raw_text: str
    evidence_ids: list[str]
    source_attribution: Literal["paper_original", "model_infer"]
    review_required: bool = False
    risk_notes: list[str] = Field(default_factory=list)


class EvidenceTraceRecord(BaseModel):
    evidence_id: str
    evidence_type: str
    source_file: str
    locator: str
    quote: str
    evidence_incomplete: bool = False


class FineTraceRecorder:
    """Claim/evidence-level trace recorder for replay and audit.

    This module does not replace the existing TraceLogger. It adds a finer-grained
    structure that can be embedded into provenance without breaking main.py or web_app.py.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or f"fine-{uuid4().hex[:12]}"
        self.steps: list[TraceStepRecord] = []
        self.claims: list[ClaimTraceRecord] = []
        self.evidence: list[EvidenceTraceRecord] = []

    def step(
        self,
        stage: str,
        status: Literal["started", "completed", "warning", "failed"],
        input_ref: dict[str, Any] | None = None,
        output_ref: dict[str, Any] | None = None,
        risks: list[dict[str, Any]] | None = None,
    ) -> None:
        self.steps.append(
            TraceStepRecord(
                step_id=f"T-{len(self.steps) + 1:04d}",
                stage=stage,
                status=status,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                input_ref=input_ref or {},
                output_ref=output_ref or {},
                risks=risks or [],
            )
        )

    def claim(self, claim: dict[str, Any]) -> None:
        self.claims.append(
            ClaimTraceRecord(
                claim_id=str(claim.get("claim_id")),
                source_file=str(claim.get("source_file", "")),
                source_location=str(claim.get("source_location") or claim.get("locator", "")),
                raw_text=str(claim.get("raw_text") or claim.get("text", "")),
                evidence_ids=list(claim.get("evidence_ids", [])),
                source_attribution=claim.get("source_attribution", "paper_original"),
                review_required=bool(claim.get("requires_human_review") or claim.get("evidence_incomplete")),
                risk_notes=list(claim.get("risk_notes", [])),
            )
        )

    def evidence_record(self, evidence: dict[str, Any]) -> None:
        self.evidence.append(
            EvidenceTraceRecord(
                evidence_id=str(evidence.get("evidence_id")),
                evidence_type=str(evidence.get("evidence_type")),
                source_file=str(evidence.get("source_file")),
                locator=str(evidence.get("locator")),
                quote=str(evidence.get("quote")),
                evidence_incomplete=bool(evidence.get("evidence_incomplete", False)),
            )
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "steps": [step.model_dump() for step in self.steps],
            "claims": [claim.model_dump() for claim in self.claims],
            "evidence": [item.model_dump() for item in self.evidence],
        }
