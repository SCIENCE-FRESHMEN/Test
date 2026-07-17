from __future__ import annotations

import shutil
import sys
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from arm_agent.pipeline import PaperToARMOrchestrator
from tools.pdf_parser_tools.figure_images import extract_pdf_figure_images, match_images_to_captions

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.resolve()
WEB_DIR = ROOT / "web"
UPLOAD_DIR = ROOT / "outputs" / "uploads"
WEB_OUTPUT_DIR = ROOT / "outputs" / "web_runs"
for directory in (UPLOAD_DIR, WEB_OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NEURONCLAW Paper-to-ARM")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/docs", StaticFiles(directory=str(ROOT / "docs")), name="docs")

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


class RunRequest(BaseModel):
    mode: str


def _safe_job(job_id: str) -> dict:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.copy()


def _set_job(job_id: str, **updates) -> None:
    with jobs_lock:
        jobs[job_id].update(updates)


def _run_job(job_id: str, paper_files: list[str]) -> None:
    _set_job(job_id, status="running", message="Generating ARM asset")
    try:
        result = PaperToARMOrchestrator(output_dir=str(WEB_OUTPUT_DIR / job_id)).run(paper_files, export_yaml=False)
        payload = result.model_dump()
        full_arm = payload["full_arm"]
        status = full_arm["metadata"]["processing_status"]
        artifact_path = None
        artifacts = full_arm.get("artifacts", [])
        if artifacts:
            artifact_path = artifacts[0]["path"]
        _set_job(job_id, status="completed", message="Completed", result=payload, arm_status=status, artifact_path=artifact_path)
    except Exception as exc:  # noqa: BLE001 - surfaced in web job state.
        _set_job(job_id, status="failed", message=str(exc), result=None)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/examples")
def examples() -> dict:
    full_papers = sorted(str(path) for path in (ROOT / "fixtures" / "full_papers").glob("*.pdf"))[:5]
    return {
        "single_success": ["brain_ECS_review.txt"],
        "failure": ["fixtures/incomplete_paper.txt"],
        "full_papers": full_papers,
    }


@app.get("/api/project-materials")
def project_materials() -> dict:
    materials = [
        {"name": "文献调研报告", "path": "/docs/literature_review_A_track.md", "score_item": "文献调研落地 / 方案设计"},
        {"name": "系统流程图", "path": "/docs/flowchart_A_track.md", "score_item": "方案设计 / 可回放流程"},
        {"name": "成功案例说明", "path": "/docs/success_case.md", "score_item": "端到端完成度 / 成功分支"},
        {"name": "失败案例说明", "path": "/docs/failure_case.md", "score_item": "失败阻断 / 安全规则"},
        {"name": "复现与测试说明", "path": "/docs/reproducibility_and_tests.md", "score_item": "代码、测试与复现"},
        {"name": "已知限制", "path": "/docs/known_limitations.md", "score_item": "局限与医学边界"},
        {"name": "PPT 大纲与演示脚本", "path": "/docs/ppt_demo_script.md", "score_item": "PPT 汇报与演示"},
        {"name": "提交检查清单", "path": "/docs/submission_checklist.md", "score_item": "最终提交清单"},
        {"name": "评分矩阵对照", "path": "/docs/scoring_matrix.md", "score_item": "评分与答辩证据"},
        {"name": "七日开发日志", "path": "/docs/day_shturl", "score_item": "开发过程说明 / 替代伪造 Git 历史"},
    ]
    return {"materials": materials}


@app.post("/api/run-example")
def run_example(request: RunRequest, background_tasks: BackgroundTasks) -> dict:
    examples_payload = examples()
    if request.mode not in examples_payload:
        raise HTTPException(status_code=400, detail="Unknown example mode")
    paper_files = examples_payload[request.mode]
    job_id = uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"job_id": job_id, "status": "queued", "message": "Queued", "input_files": paper_files}
    background_tasks.add_task(_run_job, job_id, paper_files)
    return {"job_id": job_id}


@app.post("/api/upload-run")
def upload_run(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)) -> dict:
    if not files or len(files) > 5:
        raise HTTPException(status_code=400, detail="Upload 1 to 5 PDF/TXT files")
    job_id = uuid4().hex
    job_upload_dir = UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".pdf", ".txt"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
        target = job_upload_dir / Path(file.filename or f"paper{suffix}").name
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        saved_files.append(str(target))
    with jobs_lock:
        jobs[job_id] = {"job_id": job_id, "status": "queued", "message": "Queued", "input_files": saved_files}
    background_tasks.add_task(_run_job, job_id, saved_files)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = _safe_job(job_id)
    result = job.get("result")
    if result:
        job["summary"] = _summary(result["full_arm"], result["trace_record"])
    return job


@app.get("/api/jobs/{job_id}/p0-panels")
def get_p0_panels(job_id: str) -> dict:
    job = _safe_job(job_id)
    result = job.get("result")
    if not result:
        return {"figure_evidence": [], "conflicts": [], "dry_run": {}, "evaluation": {}, "p0_trace_summary": {}}
    full_arm = result["full_arm"]
    provenance = full_arm.get("provenance", {})
    figure_evidence = []
    for figure_result in provenance.get("figure_extraction", []) or []:
        figure_evidence.extend(figure_result.get("figures", []) or [])
    return {
        "figure_evidence": figure_evidence,
        "conflicts": provenance.get("conflict_detection", {}).get("conflict_pairs", []) or [],
        "dry_run": provenance.get("dry_run_result", {}) or {},
        "evaluation": provenance.get("evaluation_result", {}) or {},
        "p0_trace_summary": provenance.get("p0_trace_summary", {}) or {},
    }


@app.get("/api/jobs/{job_id}/figure-images")
def get_figure_images(job_id: str) -> dict:
    job = _safe_job(job_id)
    result = job.get("result")
    if not result:
        return {"status": "no_result", "images": [], "figures_with_images": [], "risks": []}
    full_arm = result["full_arm"]
    provenance = full_arm.get("provenance", {})
    figure_evidence = []
    for figure_result in provenance.get("figure_extraction", []) or []:
        figure_evidence.extend(figure_result.get("figures", []) or [])
    source_files = provenance.get("source_files", []) or [full_arm.get("metadata", {}).get("source_file")]
    image_results = []
    all_images = []
    risks = []
    for source_file in source_files:
        if not source_file:
            continue
        source_captions = [item for item in figure_evidence if Path(str(item.get("source_file") or "")).name == Path(str(source_file)).name]
        result_item = extract_pdf_figure_images(source_file, captions=source_captions)
        image_results.append(result_item)
        all_images.extend(result_item.get("images", []) or [])
        risks.extend(result_item.get("risks", []) or [])
    return {
        "status": "figure_images_loaded" if all_images else "figure_images_review_required",
        "images": all_images,
        "image_results": image_results,
        "figures_with_images": match_images_to_captions(all_images, figure_evidence),
        "risks": risks,
    }


@app.get("/api/jobs/{job_id}/export/evidence-summary.csv")
def export_evidence_summary(job_id: str) -> Response:
    job = _safe_job(job_id)
    result = job.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="No ARM result available")
    full_arm = result["full_arm"]
    lines = ["claim_id,evidence_id,source_file,locator,quote"]
    evidence_by_id = {item.get("evidence_id"): item for item in full_arm.get("evidence", [])}
    for claim in full_arm.get("claims", []) or []:
        for evidence_id in claim.get("evidence_ids", []) or []:
            evidence = evidence_by_id.get(evidence_id, {})
            quote = str(evidence.get("quote", "")).replace('"', '""')
            lines.append(
                '"{}","{}","{}","{}","{}"'.format(
                    claim.get("claim_id", ""),
                    evidence_id,
                    evidence.get("source_file", ""),
                    evidence.get("locator", ""),
                    quote,
                )
            )
    return Response("\n".join(lines), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{job_id}_evidence_summary.csv"'})


@app.get("/api/jobs/{job_id}/export/figure-summary.pdf")
def export_figure_summary_pdf(job_id: str) -> Response:
    job = _safe_job(job_id)
    result = job.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="No ARM result available")
    full_arm = result["full_arm"]
    provenance = full_arm.get("provenance", {})
    captions = []
    for figure_result in provenance.get("figure_extraction", []) or []:
        captions.extend(figure_result.get("figures", []) or [])
    text = "NEURONCLAW Figure Evidence Summary\n\n" + "\n\n".join(
        f"{item.get('figure_id')} | {item.get('locator')}\n{item.get('caption')}" for item in captions
    )
    # Minimal PDF-compatible response is intentionally plain text wrapped as a
    # download artifact; the core ARM pipeline remains unchanged.
    return Response(text, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{job_id}_figure_summary.pdf"'})


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    job = _safe_job(job_id)
    artifact_path = job.get("artifact_path")
    if not artifact_path:
        raise HTTPException(status_code=404, detail="No export available")
    path = Path(artifact_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export file missing")
    return FileResponse(path, filename=path.name, media_type="application/json")


def _summary(full_arm: dict, trace_record: dict) -> dict:
    metadata = full_arm.get("metadata", {})
    provenance = full_arm.get("provenance", {})
    reference_validation = provenance.get("reference_validation", {})
    figure_extraction = provenance.get("figure_extraction", []) or []
    conflict_detection = provenance.get("conflict_detection", {}) or {}
    dry_run_result = provenance.get("dry_run_result", {}) or {}
    evaluation_result = provenance.get("evaluation_result", {}) or {}
    claims = full_arm.get("claims", [])
    evidence = full_arm.get("evidence", [])
    runbook = full_arm.get("runbook", [])
    limitations = full_arm.get("limitations", [])
    required_modules = ["metadata", "claims", "evidence", "protocol", "runbook", "eval_plan", "provenance", "limitations", "artifacts"]
    module_status = {module: module in full_arm and full_arm.get(module) is not None for module in required_modules}
    quote_only = bool(claims) and all(
        claim.get("raw_text")
        and claim.get("support_evidence_snippet")
        and claim.get("raw_text") == claim.get("support_evidence_snippet", [""])[0]
        for claim in claims
    )
    evidence_linked = bool(claims) and all(claim.get("evidence_ids") for claim in claims)
    dry_run = any(step.get("can_dry_run") for step in runbook)
    trace_tools = [call.get("tool_name") for call in trace_record.get("tool_calls", [])]
    figure_count = sum(len(item.get("figures", []) or []) for item in figure_extraction)
    conflict_count = len(conflict_detection.get("conflict_pairs", []) or [])
    review_gate = {
        "arm_modules_9": all(module_status.values()),
        "claims_at_least_5": len(claims) >= 5,
        "quote_only_claims": quote_only,
        "evidence_linked": evidence_linked,
        "ecs_tagging": metadata.get("ecs_related") is True or any(claim.get("ecs_related") for claim in claims),
        "dry_run_runbook": dry_run,
        "trace_replay": bool(trace_tools),
        "reference_validation_logged": bool(reference_validation),
        "medical_boundary": any(item.get("category") == "medical_boundary" for item in limitations),
        "failure_blocking": metadata.get("processing_status") == "failed" and full_arm.get("failure_report", {}).get("no_success_arm_generated") is True,
        "figure_caption_trace": bool(figure_extraction),
        "dry_run_evaluated": bool(dry_run_result) and bool(evaluation_result),
        "conflict_scan_logged": bool(conflict_detection),
    }
    return {
        "processing_status": metadata.get("processing_status"),
        "arm_id": metadata.get("arm_id"),
        "title": metadata.get("title"),
        "ecs_related": metadata.get("ecs_related"),
        "claims": len(claims),
        "evidence": len(evidence),
        "source_files": len(provenance.get("source_files", [])),
        "source_file_names": provenance.get("source_files", []) or [metadata.get("source_file")],
        "reference_status": reference_validation.get("status"),
        "reference_summary": reference_validation.get("summary"),
        "tool_calls": trace_tools,
        "failure_risks": trace_record.get("failure_risks", []),
        "module_status": module_status,
        "review_gate": review_gate,
        "figure_caption_count": figure_count,
        "conflict_count": conflict_count,
        "dry_run_status": dry_run_result.get("status"),
        "evaluation_status": evaluation_result.get("status"),
        "evaluation_score": evaluation_result.get("summary", {}).get("score"),
    }
