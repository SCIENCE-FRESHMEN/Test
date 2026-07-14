from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class DryRunStepResult(BaseModel):
    step_id: str
    action: str
    status: Literal["passed", "failed", "skipped"]
    expected_output: str | None = None
    observed_output: str | None = None
    errors: list[str] = Field(default_factory=list)
    review_required: bool = False


class DryRunResult(BaseModel):
    status: Literal["dry_run_passed", "dry_run_failed", "dry_run_review_required"]
    started_at_utc: str
    completed_at_utc: str
    steps: list[DryRunStepResult]
    summary: dict[str, Any]
    trace: list[dict[str, Any]] = Field(default_factory=list)


def dry_run_arm(full_arm: dict[str, Any]) -> dict[str, Any]:
    """Run a safe ARM-process dry-run.

    This does not execute laboratory experiments. It only checks whether the generated
    ARM workflow can be replayed safely with available files and module outputs.
    """
    started = datetime.now(timezone.utc).isoformat()
    trace = [{"stage": "dry_run_start"}]
    steps: list[DryRunStepResult] = []
    if full_arm.get("metadata", {}).get("processing_status") == "failed":
        completed = datetime.now(timezone.utc).isoformat()
        return DryRunResult(
            status="dry_run_review_required",
            started_at_utc=started,
            completed_at_utc=completed,
            steps=[
                DryRunStepResult(
                    step_id="DRY-FAILURE-BRANCH",
                    action="Skip success dry-run for blocked failure report",
                    status="skipped",
                    observed_output="Input was blocked before ARM success packaging.",
                    errors=[],
                    review_required=True,
                )
            ],
            summary={"total_steps": 1, "failed_steps": 0, "review_required": True, "pre_export_artifacts_allowed": True},
            trace=trace + [{"stage": "dry_run_skipped_failure_branch"}],
        ).model_dump()

    runbook = full_arm.get("runbook", []) or []
    dry_steps = [step for step in runbook if step.get("can_dry_run")]
    if not dry_steps:
        steps.append(
            DryRunStepResult(
                step_id="DRY-000",
                action="Find dry-run capable runbook step",
                status="failed",
                observed_output="No can_dry_run=True step found.",
                errors=["missing_dry_run_step"],
                review_required=True,
            )
        )
    for step in dry_steps:
        errors: list[str] = []
        for input_file in step.get("input_files", []):
            if not Path(input_file).exists():
                errors.append(f"missing_input_file:{input_file}")
        expected = step.get("expected_output")
        module_errors = _module_errors(full_arm)
        errors.extend(module_errors)
        status: Literal["passed", "failed"] = "failed" if errors else "passed"
        steps.append(
            DryRunStepResult(
                step_id=str(step.get("step_id")),
                action=str(step.get("action")),
                status=status,
                expected_output=expected,
                observed_output="ARM modules, source files, claims, evidence and trace prerequisites checked." if not errors else "Dry-run checks failed.",
                errors=errors,
                review_required=bool(errors),
            )
        )
        trace.append({"stage": "dry_run_step", "step_id": step.get("step_id"), "status": status, "errors": errors})
    failed = [step for step in steps if step.status == "failed"]
    completed = datetime.now(timezone.utc).isoformat()
    return DryRunResult(
        status="dry_run_failed" if failed else "dry_run_passed",
        started_at_utc=started,
        completed_at_utc=completed,
        steps=steps,
        summary={
            "total_steps": len(steps),
            "failed_steps": len(failed),
            "review_required": bool(failed),
            "pre_export_artifacts_allowed": full_arm.get("artifacts") == [],
        },
        trace=trace + [{"stage": "dry_run_completed", "failed_steps": len(failed)}],
    ).model_dump()


def _module_errors(full_arm: dict[str, Any]) -> list[str]:
    required = ["metadata", "claims", "evidence", "protocol", "runbook", "eval_plan", "provenance", "limitations", "artifacts"]
    errors = [f"missing_module:{module}" for module in required if module not in full_arm or full_arm.get(module) is None]
    if len(full_arm.get("claims", []) or []) < 5:
        errors.append("claims_below_minimum")
    if not full_arm.get("evidence"):
        errors.append("missing_evidence")
    return errors
