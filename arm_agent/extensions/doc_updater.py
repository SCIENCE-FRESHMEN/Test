from __future__ import annotations

from pathlib import Path
from typing import Any


def update_literature_review_metadata(search_result: dict[str, Any], report_path: str = "docs/literature_review_A_track.md") -> dict[str, Any]:
    path = Path(report_path)
    content = path.read_text(encoding="utf-8") if path.exists() else "# Literature Review\n"
    block = _metadata_block(search_result)
    marker = "<!-- AUTO_SEARCH_METADATA -->"
    end_marker = "<!-- /AUTO_SEARCH_METADATA -->"
    replacement = f"{marker}\n{block}\n{end_marker}"
    if marker in content and end_marker in content:
        start = content.index(marker)
        end = content.index(end_marker) + len(end_marker)
        content = content[:start] + replacement + content[end:]
    else:
        content += "\n\n" + replacement + "\n"
    path.write_text(content, encoding="utf-8")
    return {"status": "review_metadata_updated", "path": str(path), "records": len(search_result.get("records", []))}


def _metadata_block(search_result: dict[str, Any]) -> str:
    lines = ["## 自动检索元数据", ""]
    lines.append(f"- 检索平台：{', '.join(search_result.get('platforms', []))}")
    lines.append(f"- 检索关键词：{search_result.get('query')}")
    lines.append(f"- 时间范围：{search_result.get('year_from')} - {search_result.get('year_to')}")
    metadata = search_result.get("search_metadata", {})
    lines.append(f"- 筛选条件：{', '.join(metadata.get('screening_criteria', []))}")
    lines.append(f"- 剔除规则：{', '.join(metadata.get('exclusion_criteria', []))}")
    lines.append("")
    lines.append("| title | source | year | DOI/PMID | ECS |")
    lines.append("|---|---|---:|---|---|")
    for record in search_result.get("records", []):
        ident = record.get("doi") or record.get("pmid") or record.get("arxiv_id") or "review_required"
        lines.append(f"| {record.get('title')} | {record.get('source')} | {record.get('year')} | {ident} | {record.get('ecs_related')} |")
    return "\n".join(lines)
