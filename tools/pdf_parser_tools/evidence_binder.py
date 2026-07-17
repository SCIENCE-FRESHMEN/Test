from __future__ import annotations

from typing import Any


def bind_figures_to_claims(claims: list[dict[str, Any]], figures: list[dict[str, Any]], tables: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    evidence_links = []
    visual_items = list(figures) + list(tables or [])
    for claim in claims:
        text = str(claim.get("raw_text") or claim.get("text") or "").lower()
        linked = []
        for item in visual_items:
            ident = str(item.get("figure_id") or item.get("table_id") or "")
            caption = str(item.get("caption") or "")
            if ident.lower() in text or any(token in caption.lower() for token in text.split()[:8]):
                linked.append({
                    "claim_id": claim.get("claim_id"),
                    "visual_id": ident,
                    "locator": item.get("locator"),
                    "caption_quote": caption,
                    "source_attribution": "paper_original",
                    "review_required": False,
                })
        if not linked and visual_items:
            linked.append({
                "claim_id": claim.get("claim_id"),
                "visual_id": visual_items[0].get("figure_id") or visual_items[0].get("table_id"),
                "locator": visual_items[0].get("locator"),
                "caption_quote": visual_items[0].get("caption"),
                "source_attribution": "paper_original",
                "review_required": True,
            })
        evidence_links.extend(linked)
    return {"visual_evidence_links": evidence_links, "trace": [{"stage": "visual_evidence_bound", "links": len(evidence_links)}]}
