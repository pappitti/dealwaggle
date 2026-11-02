"""Narrow contracts for separately deployable agent integrations.

Agent outputs are proposals, never executable instructions, SQL, grants, or
public facts. A human approves proposals through /captures in this first slice.
"""

from typing import Protocol

from pydantic import BaseModel, Field


class ProviderNotConfigured(Exception):
    pass


class NeedsReview(Exception):
    pass


class ProposedFact(BaseModel):
    entity_name: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=10000)
    evidence_quote: str = Field(min_length=1, max_length=10000)


class ExtractionProvider(Protocol):
    def extract(self, text: str) -> list[ProposedFact]: ...


class EnrichmentProvider(Protocol):
    def enrich_person(self, linkedin_url: str) -> list[ProposedFact]: ...


class UnconfiguredProvider:
    def extract(self, text: str) -> list[ProposedFact]:
        raise ProviderNotConfigured("extraction")

    def enrich_person(self, linkedin_url: str) -> list[ProposedFact]:
        raise ProviderNotConfigured("enrichment")
