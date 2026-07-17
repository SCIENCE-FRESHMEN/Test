from __future__ import annotations

from typing import Any


def compute_claim_metrics(predicted_claims: list[dict[str, Any]], expert_claims: list[dict[str, Any]]) -> dict[str, Any]:
    predicted_texts = {_norm(item.get("raw_text") or item.get("text")) for item in predicted_claims}
    expert_texts = {_norm(item.get("canonical_text") or item.get("raw_text") or item.get("text")) for item in expert_claims}
    true_positive = len(predicted_texts & expert_texts)
    false_positive = len(predicted_texts - expert_texts)
    false_negative = len(expert_texts - predicted_texts)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _norm(text: object) -> str:
    return " ".join(str(text or "").lower().split())
