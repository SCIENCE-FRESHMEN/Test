from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"audit-{uuid4().hex[:10]}")
    stage: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    model_version: str | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    api_elapsed_ms: float | None = None
    claim_lineage: list[dict[str, Any]] = Field(default_factory=list)
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SecurityAuditLogger:
    def __init__(self, audit_dir: str = "outputs/audit") -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.events: list[AuditEvent] = []

    def record(self, stage: str, input_snapshot: dict[str, Any] | None = None, output_snapshot: dict[str, Any] | None = None, **kwargs: Any) -> AuditEvent:
        event = AuditEvent(stage=stage, input_snapshot=input_snapshot or {}, output_snapshot=output_snapshot or {}, **kwargs)
        self.events.append(event)
        return event

    def claim_lineage(self, claim: dict[str, Any], evidence: list[dict[str, Any]]) -> None:
        self.record("claim_lineage", input_snapshot={"claim_id": claim.get("claim_id")}, output_snapshot={"evidence_ids": claim.get("evidence_ids", [])}, claim_lineage=[{"claim": claim, "evidence": evidence}])

    def export(self, filename: str = "audit_report.json") -> dict[str, Any]:
        path = self.audit_dir / filename
        payload = {"events": [event.model_dump() for event in self.events], "event_count": len(self.events)}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "audit_exported", "path": str(path), "event_count": len(self.events)}
