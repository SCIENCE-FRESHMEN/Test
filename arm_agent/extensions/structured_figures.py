from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class StructuredTable(BaseModel):
    table_id: str
    source_file: str
    locator: str
    caption: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, str]] = Field(default_factory=list)
    source_attribution: str = "paper_original"
    review_required: bool = False


class StructuredFigurePanel(BaseModel):
    figure_id: str
    panel_id: str
    source_file: str
    locator: str
    caption_fragment: str
    source_attribution: str = "paper_original"


def parse_structured_figures(figure_result: dict[str, Any]) -> dict[str, Any]:
    panels = []
    tables = []
    for figure in figure_result.get("figures", []) or []:
        caption = str(figure.get("caption", ""))
        figure_id = str(figure.get("figure_id", "Figure"))
        source_file = str(figure.get("source_file", figure_result.get("source_file", "")))
        locator = str(figure.get("locator", f"{figure_id} caption"))
        panel_matches = list(re.finditer(r"\(([A-Za-z])\)\s*([^()]{20,240})", caption))
        for match in panel_matches:
            panels.append(StructuredFigurePanel(
                figure_id=figure_id,
                panel_id=match.group(1),
                source_file=source_file,
                locator=f"{locator} panel {match.group(1)}",
                caption_fragment=match.group(2).strip(),
            ).model_dump())
        if figure.get("evidence_type") == "table_caption" or figure_id.lower().startswith("table"):
            columns, rows = _parse_caption_table(caption)
            tables.append(StructuredTable(
                table_id=figure_id,
                source_file=source_file,
                locator=locator,
                caption=caption,
                columns=columns,
                rows=rows,
                review_required=not rows,
            ).model_dump())
    return {"panels": panels, "tables": tables, "trace": [{"stage": "structured_figure_parse", "panels": len(panels), "tables": len(tables)}]}


def _parse_caption_table(caption: str) -> tuple[list[str], list[dict[str, str]]]:
    if "|" not in caption:
        return [], []
    parts = [part.strip() for part in caption.split("|") if part.strip()]
    if len(parts) < 4:
        return [], []
    columns = ["field", "value"]
    rows = []
    for index in range(0, len(parts) - 1, 2):
        rows.append({"field": parts[index], "value": parts[index + 1]})
    return columns, rows
