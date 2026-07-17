from arm_agent.extensions.reference_completion import complete_reference_identifiers


def test_reference_completion_marks_review_when_no_match() -> None:
    result = complete_reference_identifiers([{"title": "unknown title"}])
    assert result["completed_references"][0]["completion_status"] == "reference_requires_review"


def test_reference_completion_keeps_existing_identifier() -> None:
    result = complete_reference_identifiers([{"title": "x", "doi": "10.1000/x"}])
    assert result["completed_references"][0]["completion_status"] == "already_has_identifier"


def test_reference_completion_uses_simulated_search_match() -> None:
    result = complete_reference_identifiers([{"title": "Brain extracellular space and glymphatic clearance in neurodegeneration"}], "brain extracellular space")
    assert result["completed_references"][0]["doi"] == "10.34133/cbsystems.0529"
