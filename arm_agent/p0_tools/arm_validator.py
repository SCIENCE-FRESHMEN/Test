from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


REQUIRED_ARM_MODULES = [
    "metadata",
    "claims",
    "evidence",
    "protocol",
    "runbook",
    "eval_plan",
    "provenance",
    "limitations",
    "artifacts",
]


class ValidationCheck(BaseModel):
    check_id: str
    name: str
    passed: bool
    severity: Literal["info", "medium", "high"] = "high"
    detail: dict[str, Any] = Field(default_factory=dict)
    review_required: bool = False


class ARMValidationResult(BaseModel):
    validation_passed: bool
    review_required: bool
    checks: list[ValidationCheck]
    failed_checks: list[dict[str, Any]]
    trace: list[dict[str, Any]] = Field(default_factory=list)


def validate_arm_asset(full_arm: dict[str, Any]) -> dict[str, Any]:
    """Validate ARM module completeness and provenance-critical constraints."""
    checks: list[ValidationCheck] = []
    trace = [{"stage": "arm_validation_start"}]

    module_status = {module: module in full_arm and full_arm.get(module) is not None for module in REQUIRED_ARM_MODULES}
    checks.append(
        ValidationCheck(
            check_id="ARM-001",
            name="ARM nine modules present",
            passed=all(module_status.values()),
            detail={"modules": module_status},
            review_required=not all(module_status.values()),
        )
    )

    claims = full_arm.get("claims", []) or []
    evidence = full_arm.get("evidence", []) or []
    evidence_ids = {item.get("evidence_id") for item in evidence}
    claims_have_evidence = bool(claims) and all(
        claim.get("evidence_ids") and set(claim.get("evidence_ids", [])).issubset(evidence_ids) for claim in claims
    )
    checks.append(
        ValidationCheck(
            check_id="ARM-002",
            name="Claims have linked evidence",
            passed=claims_have_evidence,
            detail={"claim_count": len(claims), "evidence_count": len(evidence)},
            review_required=not claims_have_evidence,
        )
    )

    quote_only = bool(claims) and all(
        claim.get("raw_text")
        and claim.get("support_evidence_snippet")
        and claim.get("raw_text") == claim.get("support_evidence_snippet", [""])[0]
        for claim in claims
    )
    checks.append(
        ValidationCheck(
            check_id="ARM-003",
            name="Quote-only claims",
            passed=quote_only,
            detail={"claim_count": len(claims)},
            review_required=not quote_only,
        )
    )

    model_infer_ok = all(claim.get("source_attribution") == "paper_original" for claim in claims)
    checks.append(
        ValidationCheck(
            check_id="ARM-004",
            name="Model inference is not mixed into paper claims",
            passed=model_infer_ok,
            detail={"policy": "paper claims must remain paper_original; generated workflow text is model_infer"},
            review_required=not model_infer_ok,
        )
    )

    runbook = full_arm.get("runbook", []) or []
    dry_run_present = any(step.get("can_dry_run") for step in runbook)
    checks.append(
        ValidationCheck(
            check_id="ARM-005",
            name="Dry-run capable runbook step",
            passed=dry_run_present,
            detail={"runbook_steps": len(runbook)},
            review_required=not dry_run_present,
        )
    )

    limitations = full_arm.get("limitations", []) or []
    medical_boundary = any(item.get("category") == "medical_boundary" for item in limitations)
    checks.append(
        ValidationCheck(
            check_id="ARM-006",
            name="Medical boundary limitation exists",
            passed=medical_boundary,
            detail={"limitations": len(limitations)},
            review_required=not medical_boundary,
        )
    )

    figure_quotes = [item for item in evidence if item.get("evidence_type") in {"figure_caption", "table_caption"}]
    figure_keys = {
        (item.get("source_file"), item.get("figure_or_table"), item.get("quote"))
        for item in figure_quotes
    }
    checks.append(
        ValidationCheck(
            check_id="ARM-007",
            name="Figure/table caption evidence deduplicated",
            passed=len(figure_keys) == len(figure_quotes),
            severity="medium",
            detail={"figure_caption_evidence": len(figure_quotes), "unique_caption_evidence": len(figure_keys)},
            review_required=len(figure_keys) != len(figure_quotes),
        )
    )

    failed = [check.model_dump() for check in checks if not check.passed]
    trace.append({"stage": "arm_validation_completed", "failed_count": len(failed)})
    return ARMValidationResult(
        validation_passed=not failed,
        review_required=bool(failed),
        checks=checks,
        failed_checks=failed,
        trace=trace,
    ).model_dump()
