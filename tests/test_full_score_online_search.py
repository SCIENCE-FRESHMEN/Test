from tools.literature_search_online import literature_search_online


def test_online_search_returns_ecs_records() -> None:
    result = literature_search_online("brain extracellular space", 2020, 2026)
    assert result["status"] == "search_success"
    assert result["records"]
    assert any(record["ecs_related"] for record in result["records"])


def test_online_search_year_filter() -> None:
    result = literature_search_online("brain", 2026, 2026, platforms=["PubMed"])
    assert all(record["year"] == 2026 for record in result["records"])


def test_online_search_no_result_review_required() -> None:
    result = literature_search_online("unrelatedzzzz", 2020, 2026)
    assert result["status"] == "search_review_required"
    assert result["search_metadata"]["mode"] == "offline_simulated_public_index"
