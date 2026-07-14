from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvalMetricResult(BaseModel):
    metric_id: str
    name: str
    passed: bool
    expected: str
    observed: str
    review_required: bool = False


class EvaluationResult(BaseModel):
    status: Literal["eval_passed", "eval_failed", "eval_review_required"]
    metrics: list[EvalMetricResult]
    summary: dict[str, Any]
    trace: list[dict[str, Any]] = Field(default_factory=list)


def evaluate_dry_run(full_arm: dict[str, Any], dry_run_result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate dry-run output against ARM eval_plan and core A-track requirements."""
    trace = [{"stage": "eval_start"}]
    claims = full_arm.get("claims", []) or []
    evidence = full_arm.get("evidence", []) or []
    evidence_ids = {item.get("evidence_id") for item in evidence}
    metrics = [
        EvalMetricResult(
            metric_id="EV-001",
            name="Dry-run status",
            passed=dry_run_result.get("status") == "dry_run_passed",
            expected="dry_run_passed",
            observed=str(dry_run_result.get("status")),
            review_required=dry_run_result.get("status") != "dry_run_passed",
        ),
        EvalMetricResult(
            metric_id="EV-002",
            name="At least five traceable claims",
            passed=len(claims) >= 5 and all(claim.get("evidence_ids") for claim in claims),
            expected=">=5 claims with evidence_ids",
            observed=f"{len(claims)} claims",
            review_required=len(claims) < 5,
        ),
        EvalMetricResult(
            metric_id="EV-003",
            name="Evidence IDs resolve",
            passed=all(set(claim.get("evidence_ids", [])).issubset(evidence_ids) for claim in claims),
            expected="all claim.evidence_ids exist in evidence",
            observed=f"{len(evidence_ids)} evidence ids",
        ),
        EvalMetricResult(
            metric_id="EV-004",
            name="Quote-only evidence policy",
            passed=bool(claims) and all(claim.get("raw_text") == claim.get("support_evidence_snippet", [""])[0] for claim in claims),
            expected="raw_text equals first support_evidence_snippet",
            observed="checked raw_text/support_evidence_snippet pairs",
        ),
        EvalMetricResult(
            metric_id="EV-005",
            name="Pre-export artifact handling",
            passed="artifacts" in full_arm and full_arm.get("artifacts") is not None,
            expected="artifacts module exists; empty list is allowed before export persistence",
            observed=f"artifacts_count={len(full_arm.get('artifacts', []) or [])}",
        ),
    ]
    failed = [metric for metric in metrics if not metric.passed]
    trace.append({"stage": "eval_completed", "failed_metrics": len(failed)})
    score = round(100 * (len(metrics) - len(failed)) / len(metrics), 2) if metrics else 0
    return EvaluationResult(
        status="eval_failed" if failed else "eval_passed",
        metrics=metrics,
        summary={"total_metrics": len(metrics), "failed_metrics": len(failed), "review_required": bool(failed), "score": score},
        trace=trace,
    ).model_dump()
