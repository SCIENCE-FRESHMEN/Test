from arm_agent.kg_export import export_arm_to_kg
from arm_agent.local_llm import local_generate_summary
from arm_agent.rag import build_rag_index_from_files


def test_local_rag_retrieves_ecs_text() -> None:
    index = build_rag_index_from_files(["brain_ECS_review.txt"], chunk_size=1200)
    result = index.query("extracellular space glymphatic", top_k=2)
    assert result["matches"]
    assert result["matches"][0]["score"] >= 0


def test_local_fallback_llm_marks_model_infer() -> None:
    result = local_generate_summary("This is a long neuroscience sentence about extracellular space. Another valid sentence about brain evidence.")
    assert result["model_infer"] is True
    assert result["model"] == "local-rule-fallback"


def test_c_track_kg_export() -> None:
    arm = {
        "metadata": {"arm_id": "arm-test", "title": "Test ARM"},
        "claims": [{"claim_id": "C-001", "raw_text": "ECS claim", "evidence_ids": ["E-001"], "ecs_related": True}],
        "evidence": [{"evidence_id": "E-001", "locator": "abstract paragraph 1", "source_file": "paper.txt"}],
        "limitations": [{"limitation_id": "L-001", "text": "Research only"}],
    }
    kg = export_arm_to_kg(arm)
    assert kg["status"] == "kg_export_success"
    assert any(edge["type"] == "SUPPORTED_BY" for edge in kg["edges"])
