from __future__ import annotations

from typing import Any

from tools.literature_search_online import literature_search_online


def complete_reference_identifiers(references: list[dict[str, Any]], query_hint: str = "brain extracellular space") -> dict[str, Any]:
    search = literature_search_online(query_hint)
    candidates = search.get("records", [])
    completed = []
    for ref in references:
        item = dict(ref)
        if item.get("doi") or item.get("pmid"):
            item["completion_status"] = "already_has_identifier"
            completed.append(item)
            continue
        title = str(item.get("title") or item.get("reference_text") or "").lower()
        match = None
        for candidate in candidates:
            candidate_title = str(candidate.get("title", "")).lower()
            if title and (title in candidate_title or candidate_title in title):
                match = candidate
                break
        if match:
            item["doi"] = match.get("doi")
            item["pmid"] = match.get("pmid")
            item["completion_status"] = "identifier_completed_from_simulated_search"
            item["completion_source"] = match.get("retrieval_url")
        else:
            item["completion_status"] = "reference_requires_review"
        completed.append(item)
    return {"completed_references": completed, "search_metadata": search.get("search_metadata"), "trace": search.get("trace", [])}
