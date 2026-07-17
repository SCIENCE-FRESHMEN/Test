# Full-Score Extension Update Notes

## Scope

This update adds optional full-score extension modules without deleting or restructuring the existing Paper-to-ARM pipeline. Existing commands remain compatible:

```powershell
python main.py run --input .\brain_ECS_review.txt --output-dir outputs --format json
python main.py demo --output-dir outputs
uvicorn web_app:app --host 127.0.0.1 --port 8000
```

## Newly Added Modules

- `tools/literature_search_online.py`: offline reproducible PubMed/arXiv-like literature search simulator with query metadata, DOI/PMID/arXiv fields and trace.
- `schemas/arm_increment.py`: incremental ARM merge schema and merge utility, preserving the original ARM schema.
- `arm_agent/extensions/settings_ext.py`: extension configuration defaults for online search, figure parsing and incremental export.
- `arm_agent/extensions/handoff.py`: Agent handoff planning records for figure parsing, conflict review, online search and safety review.
- `arm_agent/extensions/scheduler.py`: lightweight/heavy/online task priority scheduler.
- `arm_agent/extensions/security_guardrails.py`: prompt injection and clinical instruction blocker with standardized failure report.
- `arm_agent/extensions/evidence_trust.py`: evidence trust level and conflict-score extension metadata.
- `arm_agent/extensions/structured_figures.py`: multi-panel figure and caption-table structure parser.
- `arm_agent/extensions/reference_completion.py`: simulated identifier completion for references missing DOI/PMID.
- `arm_agent/extensions/benchmark.py`: 20-case quantitative benchmark report generator.
- `arm_agent/extensions/doc_updater.py`: automatic search metadata insertion into literature-review docs.
- `web/demo_mode.html`: optional defense demo shortcut page.
- `scripts/full_score_demo.py`: one-command extension demo and benchmark report generator.

## Newly Added Test Coverage

The test suite now covers online search, incremental ARM merge, trust scoring, prompt-injection safety, handoff, priority scheduling, structured figures, doc metadata insertion, reference completion and benchmark reporting.

Validated command:

```powershell
python -m pytest --basetemp=outputs\pytest_tmp -q
```

Current result:

```text
41 passed
```

## Compatibility Boundary

- Original `arm_agent/tools.py` remains unchanged and keeps the existing local extraction/reference validation logic.
- New search tool is placed at root package `tools/` to avoid conflict with `arm_agent/tools.py`.
- Evidence trust fields are exported as extension metadata and do not mutate the base ARM Pydantic classes.
- Figure parsing remains caption/text based and does not claim pixel-level OCR or microscopy interpretation.
- Dry-run remains ARM pipeline replay validation, not laboratory experiment reproduction.
