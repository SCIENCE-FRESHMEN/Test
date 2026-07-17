from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ARMIncrementRecord(BaseModel):
    batch_id: str
    source_files: list[str]
    claims_added: int = 0
    evidence_added: int = 0
    duplicate_claims: int = 0
    conflict_pairs: int = 0
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ARMIncrementBatch(BaseModel):
    base_arm_id: str
    mode: Literal["append", "merge_review"] = "append"
    new_paper_files: list[str]
    records: list[ARMIncrementRecord] = Field(default_factory=list)
    model_infer: bool = True


class ARMIncrementMergeResult(BaseModel):
    status: Literal["increment_merge_success", "increment_merge_review_required"]
    merged_arm: dict[str, Any]
    increment_record: ARMIncrementRecord
    provenance_patch: dict[str, Any]
    trace: list[dict[str, Any]] = Field(default_factory=list)


def merge_arm_increment(base_arm: dict[str, Any], incoming_arm: dict[str, Any], batch_id: str = "batch-append") -> dict[str, Any]:
    trace = [{"stage": "increment_merge_start", "batch_id": batch_id}]
    merged = {**base_arm}
    merged_claims = list(base_arm.get("claims", []) or [])
    merged_evidence = list(base_arm.get("evidence", []) or [])
    seen_claim_text = {claim.get("raw_text") or claim.get("text") for claim in merged_claims}
    duplicate_claims = 0
    for claim in incoming_arm.get("claims", []) or []:
        text = claim.get("raw_text") or claim.get("text")
        if text in seen_claim_text:
            duplicate_claims += 1
            continue
        seen_claim_text.add(text)
        merged_claims.append(claim)
    existing_evidence_keys = {(item.get("source_file"), item.get("locator"), item.get("quote")) for item in merged_evidence}
    evidence_added = 0
    for evidence in incoming_arm.get("evidence", []) or []:
        key = (evidence.get("source_file"), evidence.get("locator"), evidence.get("quote"))
        if key in existing_evidence_keys:
            continue
        existing_evidence_keys.add(key)
        merged_evidence.append(evidence)
        evidence_added += 1
    merged["claims"] = merged_claims
    merged["evidence"] = merged_evidence
    provenance = dict(merged.get("provenance", {}) or {})
    increments = list(provenance.get("incremental_updates", []) or [])
    source_files = list(incoming_arm.get("provenance", {}).get("source_files", []) or [])
    record = ARMIncrementRecord(
        batch_id=batch_id,
        source_files=source_files,
        claims_added=len(merged_claims) - len(base_arm.get("claims", []) or []),
        evidence_added=evidence_added,
        duplicate_claims=duplicate_claims,
        conflict_pairs=len(incoming_arm.get("provenance", {}).get("conflict_detection", {}).get("conflict_pairs", []) or []),
    )
    increments.append(record.model_dump())
    provenance["incremental_updates"] = increments
    provenance["model_infer"] = True
    provenance["increment_policy"] = "append unique claim/evidence records; preserve original ARM modules"
    merged["provenance"] = provenance
    trace.append({"stage": "increment_merge_completed", "claims_added": record.claims_added, "evidence_added": record.evidence_added})
    return ARMIncrementMergeResult(
        status="increment_merge_success",
        merged_arm=merged,
        increment_record=record,
        provenance_patch={"incremental_updates": increments, "model_infer": True},
        trace=trace,
    ).model_dump()
