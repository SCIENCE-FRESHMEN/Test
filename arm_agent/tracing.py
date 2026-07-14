from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from .schema import ToolCallRecord, TraceEvent, TraceRecord


class TraceLogger:
    def __init__(self, input_payload: dict[str, Any]) -> None:
        self.record = TraceRecord(run_id=f"run-{uuid4().hex[:12]}", input=input_payload)
        self._sequence = 0

    def event(
        self,
        stage: str,
        status: Literal["started", "completed", "blocked", "warning"],
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._sequence += 1
        self.record.events.append(
            TraceEvent(
                sequence=self._sequence,
                stage=stage,
                status=status,
                detail=detail or {},
            )
        )

    def tool_call(self, tool_name: Literal["literature_extract", "reference_validator"], tool_input: dict[str, Any], output: dict[str, Any]) -> None:
        self._sequence += 1
        self.record.tool_calls.append(
            ToolCallRecord(
                sequence=self._sequence,
                tool_name=tool_name,
                input=tool_input,
                output=output,
            )
        )

    def extraction(self, record: dict[str, Any]) -> None:
        self.record.extraction_records.append(record)

    def risk(self, code: str, message: str, severity: str = "high", detail: dict[str, Any] | None = None) -> None:
        self.record.failure_risks.append(
            {
                "code": code,
                "message": message,
                "severity": severity,
                "detail": detail or {},
            }
        )

    def validation(self, key: str, value: Any) -> None:
        self.record.validation_results[key] = value
