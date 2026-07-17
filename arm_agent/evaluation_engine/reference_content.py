from __future__ import annotations

from typing import Any


def validate_reference_content(references: list[dict[str, Any]], source_text: str) -> dict[str, Any]:
    source_norm = source_text.lower()
    records = []
    for ref in references:
        title = str(ref.get("title") or "")
        doi = ref.get("doi")
        pmid = ref.get("pmid")
        descriptor = title.lower()[:80]
        content_match = bool(title and any(token in source_norm for token in descriptor.split()[:4]))
        records.append({
            "title": title,
            "doi": doi,
            "pmid": pmid,
            "identifier_present": bool(doi or pmid),
            "content_match": content_match,
            "fake_reference_risk": bool((doi or pmid) and not content_match),
            "review_required": not bool(doi or pmid) or bool((doi or pmid) and not content_match),
        })
    return {
        "status": "reference_content_valid" if records and not any(item["review_required"] for item in records) else "reference_content_review_required",
        "records": records,
        "fake_reference_risk_count": sum(1 for item in records if item["fake_reference_risk"]),
        "trace": [{"stage": "reference_content_validation", "records": len(records)}],
    }
