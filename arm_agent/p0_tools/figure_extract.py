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
    bbox: list[float] | None = None
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
    if path.suffix.lower() == ".pdf":
        pdf_figures = _extract_pdf_captions(path, trace)
        if pdf_figures:
            return pdf_figures
        trace.append({"stage": "pdf_caption_block_fallback", "reason": "no_page_blocks_matched"})
    figures: list[FigureEvidence] = []
    for index, match in enumerate(CAPTION_PATTERN.finditer(text), start=1):
        figure_id = re.sub(r"\s+", " ", match.group("id")).strip()
        caption = re.sub(r"\s+", " ", match.group("caption")).strip()
        if _looks_like_inline_reference_caption(caption):
            trace.append({"stage": "caption_skipped_inline_reference", "figure_id": figure_id, "index": index})
            continue
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


CAPTION_BLOCK_RE = re.compile(
    r"^\s*(?P<id>Fig\.?\s*[\u00a0 ]*\d+[A-Za-z]?|Figure\s*\d+[A-Za-z]?|Table\s*\d+[A-Za-z]?|"
    r"Supplementary\s+(?:Fig\.?|Figure|Table)\s*[A-Za-z0-9]+)"
    r"\s*[\).:：．]\s*(?P<caption>.{20,1600})",
    re.I | re.S,
)


def _extract_pdf_captions(path: Path, trace: list[dict[str, Any]]) -> list[FigureEvidence]:
    try:
        import fitz  # type: ignore
    except Exception as exc:  # noqa: BLE001
        trace.append({"stage": "pdf_caption_blocks_unavailable", "error": str(exc)})
        return []
    figures: list[FigureEvidence] = []
    try:
        doc = fitz.open(str(path))
        for page_index, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks") or []
            sorted_blocks = sorted(blocks, key=lambda block: (round(float(block[1]), 1), round(float(block[0]), 1)))
            for block_index, block in enumerate(sorted_blocks):
                raw = str(block[4] or "")
                text = _clean_caption_block_text(raw)
                match = CAPTION_BLOCK_RE.match(text)
                if not match:
                    continue
                figure_id = re.sub(r"\s+", " ", match.group("id")).strip()
                caption = _extend_caption_from_neighbor_blocks(match.group("caption"), sorted_blocks, block_index)
                caption = _trim_caption_noise(caption)
                if _looks_like_inline_reference_caption(caption):
                    trace.append({"stage": "caption_skipped_inline_reference", "figure_id": figure_id, "page": page_index})
                    continue
                figures.append(_make_figure(path, figure_id, caption, page_index, [float(block[0]), float(block[1]), float(block[2]), float(block[3])]))
                trace.append({"stage": "caption_detected", "figure_id": figure_id, "page": page_index, "block_index": block_index})
        doc.close()
    except Exception as exc:  # noqa: BLE001
        trace.append({"stage": "pdf_caption_block_extract_failed", "error": str(exc)})
        return []
    return figures


def _make_figure(path: Path, figure_id: str, caption: str, page: int | None, bbox: list[float] | None) -> FigureEvidence:
    low_id = figure_id.lower()
    if "supplementary" in low_id:
        evidence_type: Literal["figure_caption", "table_caption", "supplementary_caption"] = "supplementary_caption"
    elif low_id.startswith("table"):
        evidence_type = "table_caption"
    else:
        evidence_type = "figure_caption"
    incomplete = len(caption) < 40 or caption.endswith(("Fig", "Figure", "Table"))
    return FigureEvidence(
        figure_id=figure_id,
        source_file=str(path),
        page=page,
        bbox=bbox,
        locator=f"page {page} {figure_id} caption" if page else f"{figure_id} caption",
        caption=caption[:1200],
        evidence_type=evidence_type,
        evidence_incomplete=incomplete,
        review_required=incomplete,
    )


def _clean_caption_block_text(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extend_caption_from_neighbor_blocks(caption: str, blocks: list[Any], block_index: int) -> str:
    pieces = [caption]
    _, _, _, y1, *_ = blocks[block_index]
    for next_block in blocks[block_index + 1 : block_index + 4]:
        nx0, ny0, nx1, ny1, next_text, *_ = next_block
        gap = float(ny0) - float(y1)
        cleaned = _clean_caption_block_text(str(next_text or ""))
        if not cleaned or gap > 38:
            break
        if CAPTION_BLOCK_RE.match(cleaned) or re.match(r"^(references|acknowledg|supporting information)\b", cleaned, re.I):
            break
        if _looks_like_running_header(cleaned):
            break
        pieces.append(cleaned)
        y1 = ny1
    return re.sub(r"\s+", " ", " ".join(pieces)).strip()


def _trim_caption_noise(caption: str) -> str:
    caption = re.sub(r"\s+", " ", caption).strip()
    noise_patterns = [
        r"\s+Downloaded from https?://.*$",
        r"\s+©\s*\d{4}.*$",
        r"\s+Adv\.\s*Sci\.\s*\d{4}.*$",
        r"\s+wileyonlinelibrary\.com.*$",
    ]
    for pattern in noise_patterns:
        caption = re.sub(pattern, "", caption, flags=re.I)
    return caption.strip(" ,;")


def _looks_like_running_header(text: str) -> bool:
    low = text.lower()
    return any(token in low for token in ["check for updates", "downloaded from", "wileyonlinelibrary", "advancedsciencenews.com"])


def _looks_like_inline_reference_caption(caption: str) -> bool:
    stripped = caption.strip()
    if not stripped:
        return True
    if stripped[0] in ",;)]}":
        return True
    if re.match(r"^(and|or|but|of|in|to)\b", stripped, re.I):
        return True
    return _looks_like_running_header(stripped)


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
