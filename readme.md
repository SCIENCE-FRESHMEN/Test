# NEURONCLAW A Track: Paper-to-ARM Orchestrator

This project is a runnable Paper-to-ARM prototype for the A track. It turns one to five neuroscience paper text files into a structured `full_arm` package plus a replayable `trace_record`.

## What It Implements

- ARM nine modules: `metadata`, `claims`, `evidence`, `protocol`, `runbook`, `eval_plan`, `provenance`, `limitations`, `artifacts`
- Original scientific extraction tools remain `literature_extract` and `reference_validator`; P0 review plugins are separated under `arm_agent/p0_tools`
- Success branch: extracts at least five source-located claims from `brain_ECS_review.txt`
- Failure branch: blocks incomplete input and exports a failure report instead of a partial scientific ARM
- ECS tagging in metadata, claims, and limitations
- Dry-run capable runbook step with explicit inputs, tools, outputs, and manual review flags
- P0 review plugins under `arm_agent/p0_tools`: caption-only figure/table extraction, conflict candidate detection, and ARM validation
- Dry-run and evaluator results embedded into `provenance` and displayed in the Web UI
- API rate-limit settings are centralized in `arm_agent/config/settings.py`
- JSON/YAML export and full trace replay log
- Web review gate aligned to A-track requirements
- Submission materials: literature review, flowchart, success/failure cases, reproducibility notes, known limitations, PPT script, checklist, scoring matrix

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY="sk-..."
```

The current demo is deterministic and local for reproducibility. The DeepSeek key is read from `DEEPSEEK_API_KEY` when model-backed extensions are added; do not hard-code it in source files.

DeepSeek's official quick start documents an OpenAI-compatible `base_url` of `https://api.deepseek.com`. This project defaults to `deepseek-v4-pro` in `.env.example`.

Note: installing `openai-agents` may upgrade `websockets`. On this machine pip reported a version conflict with `cozepy`; the Paper-to-ARM tests still pass.

## Run

Success case:

```powershell
python main.py run --input .\brain_ECS_review.txt --output-dir outputs --format json
```

Failure case:

```powershell
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs --format json
```

Both cases:

```powershell
python main.py demo --output-dir outputs
```

Web UI:

```powershell
uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. The page is an upload-first ARM workbench: upload 1-5 PDF/TXT files, generate ARM, inspect review-gate checks, view claims/evidence, reference validation, trace replay, raw JSON, and download the JSON export.
The "提交材料" tab links all review documents under `docs/`.

Five-paper batch case:

```powershell
$files = Get-ChildItem .\fixtures\full_papers -Filter *.pdf | Sort-Object Name | ForEach-Object { $_.FullName }
python main.py run --input @files --output-dir outputs\full_papers --format json
```

## Test

```powershell
python -m pytest
```

Expected current result:

```text
16 passed
```

## Submission Documents

- `docs/literature_review_A_track.md`
- `docs/flowchart_A_track.md`
- `docs/success_case.md`
- `docs/failure_case.md`
- `docs/reproducibility_and_tests.md`
- `docs/known_limitations.md`
- `docs/ppt_demo_script.md`
- `docs/submission_checklist.md`
- `docs/scoring_matrix.md`
- `docs/day_shturl`
- `docs/development_plan.md`

## Design Notes

The system uses a conservative controller: all claims must be backed by exact source-text quotes and locators. Pipeline-generated protocol, runbook, eval, and limitation text is marked as `model_infer` in provenance fields so it cannot be mistaken for paper evidence.

The built-in claim extractor follows a strict quote-only policy. Each extracted claim includes `raw_text`, `claim_category`, `source_location`, `support_evidence_snippet`, `conflict_evidence_snippet`, `source_attribution`, `ecs_related`, and `evidence_incomplete`. `raw_text` is copied directly from the source text and must match the supporting evidence snippet.

The reference validator records identifier, completeness, domain-fit, and duplicate/conflict checks for each extracted reference. References without DOI/PMID are marked `reference_requires_review`, and the aggregate status becomes `reference_invalid`; this is preserved in `provenance.reference_validation` and trace rather than silently discarded.

Medical boundary: outputs are research-structuring artifacts only. They do not provide diagnosis, prognosis, prescriptions, or treatment recommendations. Limitations always include animal-to-human and clinical-use warnings.
