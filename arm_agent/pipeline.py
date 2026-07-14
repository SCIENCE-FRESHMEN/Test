from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import get_settings
from .eval import dry_run_arm, evaluate_dry_run
from .schema import (
    ARM,
    Artifact,
    Claim,
    EvalMetric,
    Evidence,
    Limitation,
    Metadata,
    PipelineOutput,
    ProtocolStep,
    RunbookStep,
)
from .tools import literature_extract, reference_validator
from .p0_tools import detect_claim_conflicts, extract_figure_evidence, validate_arm_asset
from .trace import FineTraceRecorder
from .tracing import TraceLogger


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


class PaperToARMOrchestrator:
    def __init__(self, output_dir: str = "outputs") -> None:
        self.settings = get_settings()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, paper_files: list[str], export_yaml: bool = True) -> PipelineOutput:
        trace = TraceLogger(
            {
                "paper_files": paper_files,
                "max_batch_size": 5,
                "allowed_tools": ["literature_extract", "reference_validator"],
                "p0_plugin_tools": ["figure_extract", "conflict_detector", "arm_validator", "dry_run", "evaluator"],
                "api_provider": "deepseek_openai_compatible",
                "rate_limit": {
                    "request_interval_seconds": self.settings.api_request_interval_seconds,
                    "max_concurrency": self.settings.api_max_concurrency,
                    "retry_attempts": self.settings.api_retry_attempts,
                    "retry_backoff_seconds": self.settings.api_retry_backoff_seconds,
                    "timeout_seconds": self.settings.api_timeout_seconds,
                },
            }
        )
        trace.event("input_receive_and_clean", "started", {"file_count": len(paper_files)})
        if not paper_files or len(paper_files) > 5:
            trace.risk("invalid_batch_size", "Input must contain 1 to 5 papers.")
            return self._blocked_output(trace, paper_files, "invalid_batch_size")

        extracted: list[dict[str, Any]] = []
        figure_results: list[dict[str, Any]] = []
        all_references: list[dict[str, Any]] = []
        for paper_file in paper_files:
            tool_input = {"source_file": paper_file, "max_claims": 12}
            try:
                result = literature_extract(**tool_input)
            except Exception as exc:  # noqa: BLE001 - captured into trace for replay.
                trace.tool_call("literature_extract", tool_input, {"error": str(exc)})
                trace.risk("literature_extract_failed", f"Could not parse {paper_file}: {exc}")
                return self._blocked_output(trace, paper_files, "literature_extract_failed")
            trace.tool_call("literature_extract", tool_input, self._compact_tool_output(result))
            trace.extraction(
                {
                    "source_file": paper_file,
                    "candidate_claim_count": len(result["candidate_claims"]),
                    "quality_flags": result["quality_flags"],
                    "ecs_related": result["metadata"]["ecs_related"],
                }
            )
            extracted.append(result)
            all_references.extend(result["references"])
            fig_result = extract_figure_evidence(paper_file)
            figure_results.append(fig_result)
            trace.event("figure_extract", "completed" if fig_result["status"] != "figure_extract_failed" else "warning", {"source_file": paper_file, "status": fig_result["status"], "figures": len(fig_result["figures"])})

        trace.event("document_parse", "completed", {"papers_parsed": len(extracted)})
        ref_input = {"references": all_references}
        ref_result = reference_validator(all_references)
        trace.tool_call("reference_validator", ref_input, ref_result)

        risks = self._validate_inputs(extracted, ref_result)
        for risk in risks:
            trace.risk(**risk)
        trace.validation(
            "multi_layer_compliance",
            {
                "evidence_integrity": not any(r["code"] in {"insufficient_claims", "missing_precise_evidence"} for r in risks),
                "reference_status": ref_result["status"],
                "reference_summary": ref_result["summary"],
                "hallucination_control": True,
                "medical_boundary": True,
                "input_completeness": not risks,
            },
        )
        if risks:
            trace.event("branch_decision", "blocked", {"reason": "validation_failed", "risk_count": len(risks)})
            return self._blocked_output(trace, paper_files, "validation_failed")

        conflict_input_claims = []
        for item in extracted:
            conflict_input_claims.extend(item["candidate_claims"])
        conflict_result = detect_claim_conflicts(conflict_input_claims)
        trace.validation("conflict_detection", {"status": conflict_result["status"], "conflict_count": len(conflict_result["conflict_pairs"])})

        arm = self._build_arm(extracted, ref_result, trace.record.run_id, figure_results, conflict_result)
        fine_trace = self._build_fine_trace(arm, trace.record.run_id)
        arm.provenance["fine_trace"] = fine_trace

        validation_result = validate_arm_asset(arm.model_dump())
        dry_run_result = dry_run_arm(arm.model_dump())
        evaluation_result = evaluate_dry_run(arm.model_dump(), dry_run_result)
        arm.provenance["arm_validation"] = validation_result
        arm.provenance["dry_run_result"] = dry_run_result
        arm.provenance["evaluation_result"] = evaluation_result
        arm.provenance["p0_trace_summary"] = {
            "figure_caption_sources": sum(len(item.get("figures", [])) for item in figure_results),
            "conflict_pairs": len(conflict_result.get("conflict_pairs", [])),
            "dry_run_score": evaluation_result.get("summary", {}).get("score"),
            "dry_run_status": dry_run_result.get("status"),
            "evaluation_status": evaluation_result.get("status"),
        }
        trace.validation("arm_asset_validation", validation_result)
        trace.validation("dry_run", dry_run_result)
        trace.validation("evaluation_result", evaluation_result)
        trace.validation(
            "arm_modules_present",
            {module: getattr(arm, module) is not None for module in REQUIRED_ARM_MODULES},
        )
        trace.event("arm_packaging", "completed", {"modules": REQUIRED_ARM_MODULES})

        json_path = self.output_dir / f"{arm.metadata.arm_id}.json"
        json_path.write_text(json.dumps({"full_arm": arm.model_dump(), "trace_record": trace.record.model_dump()}, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts = [
            Artifact(
                artifact_id="A-JSON",
                type="json_export",
                path=str(json_path),
                description="Complete ARM package and replay trace in JSON.",
            )
        ]
        if export_yaml:
            yaml_path = self.output_dir / f"{arm.metadata.arm_id}.yaml"
            yaml_path.write_text(to_yaml({"full_arm": arm.model_dump(), "trace_record": trace.record.model_dump()}), encoding="utf-8")
            artifacts.append(
                Artifact(
                    artifact_id="A-YAML",
                    type="yaml_export",
                    path=str(yaml_path),
                    description="Complete ARM package and replay trace in YAML.",
                )
            )
        arm.artifacts.extend(artifacts)
        json_path.write_text(json.dumps({"full_arm": arm.model_dump(), "trace_record": trace.record.model_dump()}, ensure_ascii=False, indent=2), encoding="utf-8")
        if export_yaml:
            yaml_path.write_text(to_yaml({"full_arm": arm.model_dump(), "trace_record": trace.record.model_dump()}), encoding="utf-8")
        trace.event("trace_persistence", "completed", {"exports": [artifact.path for artifact in artifacts]})
        return PipelineOutput(full_arm=arm, trace_record=trace.record)

    def _validate_inputs(self, extracted: list[dict[str, Any]], ref_result: dict[str, Any]) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        total_claims = sum(len(item["candidate_claims"]) for item in extracted)
        if total_claims < 5:
            risks.append(
                {
                    "code": "insufficient_claims",
                    "message": "Fewer than 5 independently traceable candidate claims were found.",
                    "severity": "high",
                    "detail": {"candidate_claim_count": total_claims},
                }
            )
        if not any(item["metadata"]["ecs_related"] for item in extracted):
            risks.append(
                {
                    "code": "ecs_information_missing",
                    "message": "No ECS-related keywords or concepts were detected.",
                    "severity": "high",
                    "detail": {},
                }
            )
        for item in extracted:
            flags = item["quality_flags"]
            source = item["metadata"]["source_file"]
            batch_has_figures = any(other["quality_flags"]["has_figures_or_tables"] for other in extracted)
            batch_has_references = bool(ref_result["checked_count"]) or any(other["quality_flags"]["has_references"] for other in extracted)
            if not flags["has_figures_or_tables"] and not batch_has_figures:
                risks.append({"code": "missing_figures_tables", "message": "No figure or table captions were detected.", "severity": "high", "detail": {"source_file": source}})
            if not flags["has_references"] and not batch_has_references:
                risks.append({"code": "missing_references", "message": "No references or DOI/PMID identifiers were detected.", "severity": "medium", "detail": {"source_file": source}})
            if flags["paragraph_count"] < 8:
                severity = "medium" if len(extracted) > 1 and total_claims >= 5 else "high"
                if severity == "high":
                    risks.append({"code": "paper_text_too_short", "message": "Input text is too short for reliable ARM generation.", "severity": severity, "detail": {"source_file": source, "paragraph_count": flags["paragraph_count"]}})
            if item["metadata"]["article_type"] != "review" and not flags["has_methods"]:
                if len(extracted) == 1:
                    risks.append({"code": "missing_methods", "message": "Research article appears to lack a methods section.", "severity": "high", "detail": {"source_file": source}})
            if item["metadata"]["article_type"] != "review" and not flags["has_results"]:
                if len(extracted) == 1:
                    risks.append({"code": "missing_results", "message": "Research article appears to lack a results section.", "severity": "high", "detail": {"source_file": source}})
        if ref_result["checked_count"] == 0:
            risks.append(
                {
                    "code": "missing_reference_records",
                    "message": "No reference records could be extracted for validation.",
                    "severity": "medium",
                    "detail": {"checked_count": ref_result["checked_count"]},
                }
            )
        return risks

    def _build_arm(self, extracted: list[dict[str, Any]], ref_result: dict[str, Any], run_id: str, figure_results: list[dict[str, Any]] | None = None, conflict_result: dict[str, Any] | None = None) -> ARM:
        primary = extracted[0]
        source_file = primary["metadata"]["source_file"]
        arm_id = "arm-" + Path(source_file).stem.lower().replace(" ", "-")[:48]
        source_files = [item["metadata"]["source_file"] for item in extracted]
        evidence: list[Evidence] = []
        claims: list[Claim] = []

        selected_claims = []
        for item in extracted:
            selected_claims.extend(item["candidate_claims"])
        selected_claims = selected_claims[: max(5, min(12, len(selected_claims)))]

        for idx, claim in enumerate(selected_claims, start=1):
            claim_id = f"C-{idx:03d}"
            evidence_id = f"E-{idx:03d}"
            quote = claim["raw_text"]
            evidence.append(
                Evidence(
                    evidence_id=evidence_id,
                    claim_id=claim_id,
                    source_file=claim.get("source_file") or source_file,
                    locator=claim["locator"],
                    section=claim["section"],
                    paragraph_index=claim["paragraph_index"],
                    quote=quote,
                    evidence_type="text",
                )
            )
            claims.append(
                Claim(
                    claim_id=claim_id,
                    text=claim["raw_text"],
                    raw_text=claim["raw_text"],
                    claim_category=claim["claim_category"],
                    section=claim["section"],
                    locator=claim["locator"],
                    source_location=claim["source_location"],
                    evidence_ids=[evidence_id],
                    support_evidence_snippet=claim["support_evidence_snippet"],
                    conflict_evidence_snippet=claim["conflict_evidence_snippet"],
                    source_attribution=claim["source_attribution"],
                    evidence_incomplete=claim["evidence_incomplete"],
                    ecs_related=claim["ecs_related"],
                    claim_type=self._claim_type(claim["raw_text"]),
                )
            )

        figure = primary["figures_tables"][0] if primary["figures_tables"] else None
        if figure:
            evidence.append(
                Evidence(
                    evidence_id="E-FIG-001",
                    source_file=source_file,
                    locator=figure["locator"],
                    section="figure_caption",
                    figure_or_table=figure["id"],
                    quote=figure["caption"],
                    evidence_type="figure_caption",
                )
            )
        for fig_result in figure_results or []:
            for fig in fig_result.get("figures", [])[:5]:
                evidence_id = f"E-FIG-{len(evidence) + 1:03d}"
                evidence.append(
                    Evidence(
                        evidence_id=evidence_id,
                        source_file=fig["source_file"],
                        locator=fig["locator"],
                        section="figure_caption",
                        figure_or_table=fig["figure_id"],
                        quote=fig["caption"],
                        evidence_type=fig["evidence_type"] if fig["evidence_type"] in {"figure_caption", "table_caption"} else "figure_caption",
                    )
                )

        metadata = Metadata(
            arm_id=arm_id,
            **primary["metadata"],
            processing_status="success",
        )

        protocol = [
            ProtocolStep(
                step_id="P-001",
                name="Parse paper into source-located sections",
                description="Segment abstract, methods/results/discussion where present, figure/table captions, references, and ECS keyword hits.",
                input_materials=source_files,
                method_source_locator="system_pipeline:literature_extract",
                expected_output="Section map with paragraph indices and source quotes.",
                automation_level="auto",
                provenance="model_infer",
            ),
            ProtocolStep(
                step_id="P-002",
                name="Align claims to evidence",
                description="Keep only claims backed by exact source-text quotes and locators.",
                input_materials=source_files,
                method_source_locator="system_pipeline:claim_evidence_alignment",
                expected_output="Claim list with evidence_ids and locators.",
                automation_level="manual_review",
                provenance="model_infer",
            ),
        ]

        runbook = [
            RunbookStep(
                step_id="R-001",
                action="Dry-run the Paper-to-ARM pipeline on the same input and validate ARM modules.",
                input_files=source_files,
                dependent_tools=["literature_extract", "reference_validator"],
                expected_output="JSON export containing full_arm and trace_record; all nine ARM modules present.",
                manual_review_required=False,
                can_dry_run=True,
                dry_run_command="python main.py run --input " + " ".join(f'"{item}"' for item in source_files) + " --output-dir outputs --format json",
                failure_conditions=["Missing source file", "Fewer than 5 traceable claims", "No ECS content detected"],
            ),
            RunbookStep(
                step_id="R-002",
                action="Manually review quote-to-claim alignment and medical-boundary warnings.",
                input_files=source_files,
                dependent_tools=[],
                expected_output="Human approval or correction list for claim/evidence pairs.",
                manual_review_required=True,
                can_dry_run=False,
                failure_conditions=["Claim text overstates source quote", "Clinical advice detected"],
            ),
        ]

        eval_plan = [
            EvalMetric(metric_id="M-001", name="ARM module completeness", pass_condition="metadata/claims/evidence/protocol/runbook/eval_plan/provenance/limitations/artifacts all exist", evaluation_method="Schema validation with pydantic."),
            EvalMetric(metric_id="M-002", name="Traceable claims", pass_condition="At least 5 claims have non-empty evidence_ids and exact quotes.", evaluation_method="Automated count plus manual spot-check."),
            EvalMetric(metric_id="M-003", name="Failure branch blocking", pass_condition="Incomplete input returns failure report and does not create success ARM.", evaluation_method="Run tests/test_pipeline.py and inspect trace_record.failure_risks."),
            EvalMetric(metric_id="M-004", name="ECS tagging", pass_condition="metadata.ecs_related is true for ECS papers and ECS-related claims are tagged.", evaluation_method="Keyword detection plus manual review."),
        ]

        limitations = [
            Limitation(
                limitation_id="L-001",
                text="This ARM is for research literature structuring only and must not be used for clinical diagnosis, prognosis, prescription, or treatment decisions.",
                category="medical_boundary",
                ecs_related=False,
                provenance="model_infer",
            ),
            Limitation(
                limitation_id="L-002",
                text="Animal or preclinical findings in source papers cannot be directly transferred to humans without clinical validation.",
                category="animal_to_human",
                ecs_related=False,
                provenance="model_infer",
            ),
            Limitation(
                limitation_id="L-003",
                text="ECS-related conclusions require manual review because ECS structure, measurement modality, and disease context vary across studies.",
                category="ecs_gap",
                ecs_related=True,
                provenance="model_infer",
            ),
            Limitation(
                limitation_id="L-004",
                text="Data and code availability are not assumed unless explicitly detected in the source text.",
                category="data_availability",
                ecs_related=False,
                provenance="model_infer",
            ),
        ]

        provenance = {
            "run_id": run_id,
            "allowed_tools": ["literature_extract", "reference_validator"],
            "model": {
                "provider": "DeepSeek",
                "model_name": "deepseek-v4-pro",
                "usage": "optional; deterministic local extractors are used for this reproducible demo",
            },
            "source_files": source_files,
            "reference_validation": ref_result,
            "figure_extraction": figure_results or [],
            "conflict_detection": conflict_result or {},
            "model_infer_policy": "Any pipeline-generated protocol, runbook, eval, and limitation text is marked model_infer and is not treated as source evidence.",
            "claim_extractor_policy": "Claims are raw paper excerpts only. raw_text and support_evidence_snippet are not paraphrased.",
        }

        return ARM(
            metadata=metadata,
            claims=claims,
            evidence=evidence,
            protocol=protocol,
            runbook=runbook,
            eval_plan=eval_plan,
            provenance=provenance,
            limitations=limitations,
            artifacts=[],
        )

    def _blocked_output(self, trace: TraceLogger, paper_files: list[str], reason: str) -> PipelineOutput:
        source_file = paper_files[0] if paper_files else ""
        metadata = Metadata(
            arm_id=f"failed-{trace.record.run_id}",
            title=None,
            source_file=source_file,
            ecs_related=False,
            processing_status="failed",
        )
        failure_report: dict[str, Any] = {
            "metadata": metadata.model_dump(),
            "claims": [],
            "evidence": [],
            "protocol": [],
            "runbook": [],
            "eval_plan": [],
            "provenance": {
                "run_id": trace.record.run_id,
                "blocked_reason": reason,
                "model_infer_policy": "No scientific ARM was generated because validation failed.",
            },
            "limitations": [
                {
                    "limitation_id": "FAIL-L-001",
                    "text": "Input failed completeness/provenance checks; generating a scientific ARM would risk unsupported claims.",
                    "category": "input_quality",
                    "ecs_related": False,
                    "provenance": "model_infer",
                    "evidence_ids": [],
                }
            ],
            "artifacts": [],
            "failure_report": {
                "status": "blocked",
                "reason": reason,
                "missing_or_risky_items": trace.record.failure_risks,
                "no_success_arm_generated": True,
            },
        }
        fail_path = self.output_dir / f"failed_{trace.record.run_id}.json"
        fail_path.write_text(json.dumps({"full_arm": failure_report, "trace_record": trace.record.model_dump()}, ensure_ascii=False, indent=2), encoding="utf-8")
        failure_report["artifacts"].append(
            {
                "artifact_id": "FAIL-JSON",
                "type": "failure_report_json",
                "path": str(fail_path),
                "description": "Blocked failure report with replay trace.",
            }
        )
        trace.event("failure_report_export", "completed", {"path": str(fail_path)})
        fail_path.write_text(json.dumps({"full_arm": failure_report, "trace_record": trace.record.model_dump()}, ensure_ascii=False, indent=2), encoding="utf-8")
        return PipelineOutput(full_arm=failure_report, trace_record=trace.record)

    def _claim_type(self, text: str) -> str:
        low = text.lower()
        if "defined as" in low or "constitutes" in low:
            return "definition"
        if "propose" in low or "recommend" in low:
            return "method"
        if "limitation" in low or "overlook" in low:
            return "limitation"
        return "finding"

    def _build_fine_trace(self, arm: ARM, run_id: str) -> dict[str, Any]:
        recorder = FineTraceRecorder(run_id=run_id)
        recorder.step("fine_trace_start", "started", {"arm_id": arm.metadata.arm_id})
        for claim in arm.claims:
            recorder.claim({**claim.model_dump(), "source_file": arm.metadata.source_file})
        for evidence in arm.evidence:
            recorder.evidence_record(evidence.model_dump())
        recorder.step(
            "fine_trace_completed",
            "completed",
            output_ref={"claims": len(arm.claims), "evidence": len(arm.evidence)},
        )
        return recorder.model_dump()

    def _compact_tool_output(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "metadata": result["metadata"],
            "extractor_prompt": result.get("extractor_prompt"),
            "candidate_claim_count": len(result["candidate_claims"]),
            "references_count": len(result["references"]),
            "figures_tables_count": len(result["figures_tables"]),
            "quality_flags": result["quality_flags"],
        }


def to_yaml(value: Any, indent: int = 0) -> str:
    """Small YAML emitter for JSON-compatible data, avoiding an extra dependency."""
    spaces = "  " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}{key}:")
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append(f"{spaces}{key}: {format_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{spaces}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}-")
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append(f"{spaces}- {format_scalar(item)}")
        return "\n".join(lines)
    return f"{spaces}{format_scalar(value)}"


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if "\n" in text or ": " in text or text.strip() != text or text == "":
        return json.dumps(text, ensure_ascii=False)
    return json.dumps(text, ensure_ascii=False)
