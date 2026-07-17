from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertClaim(BaseModel):
    claim_id: str
    canonical_text: str
    acceptable_quotes: list[str] = Field(default_factory=list)
    source_location: str | None = None
    ecs_related: bool = False


class ExpertAnnotatedARM(BaseModel):
    dataset_id: str
    source_file: str
    expert_claims: list[ExpertClaim]
    notes: str | None = None
