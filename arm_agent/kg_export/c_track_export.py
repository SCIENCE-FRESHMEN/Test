from __future__ import annotations

from typing import Any


def export_arm_to_kg(full_arm: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    edges = []
    metadata = full_arm.get("metadata", {})
    arm_id = metadata.get("arm_id", "arm")
    nodes.append({"id": arm_id, "type": "ARMAsset", "label": metadata.get("title") or arm_id})
    for claim in full_arm.get("claims", []) or []:
        claim_id = claim.get("claim_id")
        nodes.append({"id": claim_id, "type": "Claim", "label": (claim.get("raw_text") or claim.get("text") or "")[:120], "ecs_related": claim.get("ecs_related")})
        edges.append({"source": arm_id, "target": claim_id, "type": "HAS_CLAIM"})
        for evidence_id in claim.get("evidence_ids", []) or []:
            edges.append({"source": claim_id, "target": evidence_id, "type": "SUPPORTED_BY"})
    for evidence in full_arm.get("evidence", []) or []:
        nodes.append({"id": evidence.get("evidence_id"), "type": "Evidence", "label": evidence.get("locator"), "source_file": evidence.get("source_file")})
    for limitation in full_arm.get("limitations", []) or []:
        limitation_id = limitation.get("limitation_id")
        nodes.append({"id": limitation_id, "type": "Limitation", "label": limitation.get("text")})
        edges.append({"source": arm_id, "target": limitation_id, "type": "HAS_LIMITATION"})
    return {"status": "kg_export_success", "nodes": nodes, "edges": edges, "schema": "C-track-compatible-v0", "trace": [{"stage": "arm_to_kg_export", "nodes": len(nodes), "edges": len(edges)}]}
