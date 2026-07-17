from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ParsedFigure(BaseModel):
    figure_id: str
    page: int | None = None
    caption: str
    locator: str
    source_file: str
    source_attribution: Literal["paper_original"] = "paper_original"


class ParsedTable(BaseModel):
    table_id: str
    page: int | None = None
    caption: str
    rows: list[list[str]] = Field(default_factory=list)
    locator: str
    source_file: str
    source_attribution: Literal["paper_original"] = "paper_original"


class PDFParseResult(BaseModel):
    status: Literal["pdf_parse_success", "pdf_parse_review_required", "pdf_parse_failed"]
    source_file: str
    text: str = ""
    figures: list[ParsedFigure] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


CAPTION_RE = re.compile(r"(?P<id>Fig\.?\s*\d+[A-Za-z]?|Figure\s*\d+[A-Za-z]?|Table\s*\d+[A-Za-z]?)[.)\s:]+(?P<caption>.{30,900}?)(?=\n\s*(?:Fig\.?\s*\d+|Figure\s*\d+|Table\s*\d+)|\Z)", re.I | re.S)


def parse_pdf_document(source_file: str) -> dict[str, Any]:
    trace = [{"stage": "pdf_parse_start", "source_file": source_file}]
    risks: list[dict[str, Any]] = []
    path = Path(source_file)
    try:
        text, table_rows = _read_pdf_with_best_available_parser(path, trace)
        figures, tables = _extract_captions(path, text, table_rows)
        if not text.strip():
            risks.append({"code": "empty_pdf_text", "severity": "high", "review_required": True})
        if not figures and not tables:
            risks.append({"code": "missing_pdf_figures_tables", "severity": "medium", "review_required": True})
        status = "pdf_parse_success" if text.strip() and not risks else "pdf_parse_review_required"
        trace.append({"stage": "pdf_parse_completed", "status": status, "figures": len(figures), "tables": len(tables)})
        return PDFParseResult(status=status, source_file=str(path), text=text, figures=figures, tables=tables, risks=risks, trace=trace).model_dump()
    except Exception as exc:  # noqa: BLE001
        risks.append({"code": "pdf_parse_failed", "message": str(exc), "severity": "high", "review_required": True})
        trace.append({"stage": "pdf_parse_failed", "error": str(exc)})
        return PDFParseResult(status="pdf_parse_failed", source_file=str(path), risks=risks, trace=trace).model_dump()


def _read_pdf_with_best_available_parser(path: Path, trace: list[dict[str, Any]]) -> tuple[str, list[list[str]]]:
    table_rows: list[list[str]] = []
    try:
        import pdfplumber  # type: ignore

        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text_parts.append(f"\n[page {page_index}]\n" + (page.extract_text() or ""))
                for table in page.extract_tables() or []:
                    for row in table or []:
                        table_rows.append([str(cell or "") for cell in row])
        trace.append({"stage": "pdfplumber_parse_used", "pages": len(text_parts), "table_rows": len(table_rows)})
        return "\n".join(text_parts), table_rows
    except Exception as exc:  # noqa: BLE001
        trace.append({"stage": "pdfplumber_unavailable", "reason": str(exc)})
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception:  # noqa: BLE001
        from pypdf import PdfReader  # type: ignore
    reader = PdfReader(str(path))
    text_parts = []
    for page_index, page in enumerate(reader.pages, start=1):
        text_parts.append(f"\n[page {page_index}]\n" + (page.extract_text() or ""))
    trace.append({"stage": "pypdf_parse_used", "pages": len(text_parts)})
    return "\n".join(text_parts), table_rows


def _extract_captions(path: Path, text: str, table_rows: list[list[str]]) -> tuple[list[ParsedFigure], list[ParsedTable]]:
    figures: list[ParsedFigure] = []
    tables: list[ParsedTable] = []
    for match in CAPTION_RE.finditer(text):
        item_id = re.sub(r"\s+", " ", match.group("id")).strip()
        caption = re.sub(r"\s+", " ", match.group("caption")).strip()
        page_match = re.findall(r"\[page (\d+)\]", text[: match.start()])
        page = int(page_match[-1]) if page_match else None
        if item_id.lower().startswith("table"):
            tables.append(ParsedTable(table_id=item_id, page=page, caption=caption, rows=table_rows[:20], locator=f"{item_id} caption", source_file=str(path)))
        else:
            figures.append(ParsedFigure(figure_id=item_id, page=page, caption=caption, locator=f"{item_id} caption", source_file=str(path)))
    return figures, tables
