from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class OnlinePaperRecord(BaseModel):
    source: Literal["PubMed", "arXiv"]
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int
    doi: str | None = None
    pmid: str | None = None
    arxiv_id: str | None = None
    abstract: str
    keywords: list[str] = Field(default_factory=list)
    ecs_related: bool = False
    retrieval_url: str


class LiteratureSearchResult(BaseModel):
    status: Literal["search_success", "search_review_required"]
    query: str
    year_from: int
    year_to: int
    platforms: list[str]
    records: list[OnlinePaperRecord]
    search_metadata: dict[str, Any]
    trace: list[dict[str, Any]] = Field(default_factory=list)


MOCK_CORPUS = [
    OnlinePaperRecord(
        source="PubMed",
        title="Brain extracellular space and glymphatic clearance in neurodegeneration",
        authors=["Han H", "Dai H"],
        year=2026,
        doi="10.34133/cbsystems.0529",
        pmid="40652029",
        abstract="This review discusses extracellular space, brain interstitial fluid, glymphatic clearance, and disease mechanisms.",
        keywords=["extracellular space", "glymphatic", "brain", "ECS"],
        ecs_related=True,
        retrieval_url="https://pubmed.ncbi.nlm.nih.gov/?term=brain+extracellular+space",
    ),
    OnlinePaperRecord(
        source="arXiv",
        title="LLM agents for biomedical evidence structuring",
        authors=["Example A", "Example B"],
        year=2025,
        doi="10.48550/arXiv.2501.00001",
        arxiv_id="2501.00001",
        abstract="A simulated record for agentic biomedical literature structuring and provenance tracking.",
        keywords=["AI agent", "biomedical", "evidence"],
        ecs_related=False,
        retrieval_url="https://arxiv.org/search/?query=biomedical+agent",
    ),
    OnlinePaperRecord(
        source="PubMed",
        title="Interstitial fluid transport and amyloid clearance in brain disorders",
        authors=["Iliff J", "Wang M"],
        year=2020,
        doi="10.1126/scitranslmed.3003748",
        pmid="22896675",
        abstract="Brain interstitial solute clearance pathways are relevant to amyloid and neurodegenerative mechanisms.",
        keywords=["interstitial fluid", "amyloid", "clearance", "brain"],
        ecs_related=True,
        retrieval_url="https://pubmed.ncbi.nlm.nih.gov/22896675/",
    ),
]


def literature_search_online(query: str, year_from: int = 2020, year_to: int = 2026, max_records: int = 10, platforms: list[str] | None = None) -> dict[str, Any]:
    """Return reproducible PubMed/arXiv-like neuroscience search records.

    This is an offline deterministic simulator. It records realistic retrieval
    metadata for demo and tests without claiming live network access.
    """
    selected_platforms = platforms or ["PubMed", "arXiv"]
    trace = [{"stage": "literature_search_start", "query": query, "year_from": year_from, "year_to": year_to, "platforms": selected_platforms}]
    tokens = {token.lower() for token in query.replace("/", " ").replace("-", " ").split() if token.strip()}
    records = []
    for record in MOCK_CORPUS:
        haystack = " ".join([record.title, record.abstract, " ".join(record.keywords)]).lower()
        if record.source not in selected_platforms or not (year_from <= record.year <= year_to):
            continue
        if tokens and not any(token in haystack for token in tokens):
            continue
        records.append(record)
        if len(records) >= max_records:
            break
    trace.append({"stage": "literature_search_completed", "record_count": len(records)})
    return LiteratureSearchResult(
        status="search_success" if records else "search_review_required",
        query=query,
        year_from=year_from,
        year_to=year_to,
        platforms=selected_platforms,
        records=records,
        search_metadata={
            "mode": "offline_simulated_public_index",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "screening_criteria": ["neuroscience_or_biomedical", "year_range", "identifier_available_when_present"],
            "exclusion_criteria": ["non_scientific_chatbot_only", "missing_source_context"],
        },
        trace=trace,
    ).model_dump()
