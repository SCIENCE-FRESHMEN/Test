from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from arm_agent.tools import normalize_text, read_paper_text


class FigureEvidence(BaseModel):
    figure_id: str
    source_file: str
    page: int | None = None
    locator: str
    caption: str
    evidence_type: Literal["figure_caption", "table_caption", "supplementary_caption"]
    evidence_incomplete: bool = False
    review_required: bool = False
    source_attribution: Literal["paper_original", "model_infer"] = "paper_original"


class FigureExtractResult(BaseModel):
    status: Literal["figure_extract_success", "figure_extract_review_required", "figure_extract_failed"]
    source_file: str
    figures: list[FigureEvidence] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


CAPTION_PATTERN = re.compile(
    r"(?P<id>Fig\.?\s*[\u00a0 ]*\d+[A-Za-z]?|Figure\s*\d+[A-Za-z]?|Table\s*\d+[A-Za-z]?|"
    r"Supplementary\s+(?:Fig\.?|Figure|Table)\s*[A-Za-z0-9]+)"
    r"[.)\s:]*\s*(?P<caption>.{30,1200}?)(?=\n\s*(?:Fig\.?\s*[\u00a0 ]*\d+|Figure\s*\d+|Table\s*\d+|Supplementary)|\Z)",
    re.I | re.S,
)


def extract_figure_evidence(source_file: str) -> dict[str, Any]:
    """Extract figure/table/supplementary captions as source-text evidence.

    Scope is deliberately conservative: this tool parses extractable PDF/TXT text and
    caption strings only. It does not interpret image pixels, table cells, microscopy
    panels, or plotted values.
    """
    trace: list[dict[str, Any]] = [{"stage": "figure_extract_start", "source_file": source_file}]
    risks: list[dict[str, Any]] = []
    try:
        path = Path(source_file)
        text = normalize_text(read_paper_text(path))
        figures = _dedupe_figures(_extract_captions(text, path, trace))
        if not figures:
            risks.append(
                {
                    "code": "figure_caption_missing",
                    "message": "No Figure/Table/Supplementary captions were extracted from source text.",
                    "severity": "medium",
                    "review_required": True,
                }
            )
        status = "figure_extract_success" if figures else "figure_extract_review_required"
        trace.append({"stage": "figure_extract_completed", "status": status, "caption_count": len(figures)})
        return FigureExtractResult(status=status, source_file=str(path), figures=figures, risks=risks, trace=trace).model_dump()
    except Exception as exc:  # noqa: BLE001 - failure is returned as reviewable trace data.
        risks.append(
            {
                "code": "figure_extract_failed",
                "message": str(exc),
                "severity": "high",
                "review_required": True,
            }
        )
        trace.append({"stage": "figure_extract_failed", "error": str(exc)})
        return FigureExtractResult(status="figure_extract_failed", source_file=source_file, risks=risks, trace=trace).model_dump()


def _extract_captions(text: str, path: Path, trace: list[dict[str, Any]]) -> list[FigureEvidence]:
    figures: list[FigureEvidence] = []
    for index, match in enumerate(CAPTION_PATTERN.finditer(text), start=1):
        figure_id = re.sub(r"\s+", " ", match.group("id")).strip()
        caption = re.sub(r"\s+", " ", match.group("caption")).strip()
        low_id = figure_id.lower()
        if "supplementary" in low_id:
            evidence_type: Literal["figure_caption", "table_caption", "supplementary_caption"] = "supplementary_caption"
        elif low_id.startswith("table"):
            evidence_type = "table_caption"
        else:
            evidence_type = "figure_caption"
        incomplete = len(caption) < 40 or caption.endswith(("Fig", "Figure", "Table"))
        figures.append(
            FigureEvidence(
                figure_id=figure_id,
                source_file=str(path),
                locator=f"{figure_id} caption",
                caption=caption[:1200],
                evidence_type=evidence_type,
                evidence_incomplete=incomplete,
                review_required=incomplete,
            )
        )
        trace.append({"stage": "caption_detected", "figure_id": figure_id, "index": index})
    return figures


def _dedupe_figures(figures: list[FigureEvidence]) -> list[FigureEvidence]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[FigureEvidence] = []
    for figure in figures:
        key = (
            figure.source_file.lower(),
            re.sub(r"\s+", "", figure.figure_id.lower()),
            re.sub(r"\W+", "", figure.caption.lower())[:160],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(figure)
    return deduped
