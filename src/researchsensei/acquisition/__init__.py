"""Acquisition module for paper search adapters."""

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition.dblp_adapter import DBLPAdapter
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter
from researchsensei.acquisition.paper_search_mcp_adapter import PaperSearchMcpAdapter, paper_search_mcp_available
from researchsensei.acquisition.semantic_scholar_adapter import SemanticScholarAdapter
from researchsensei.core.config import ConfigService


def make_default_search_adapter() -> PaperSearchMcpAdapter:
    search = ConfigService().load().search
    return PaperSearchMcpAdapter(
        sources=search.sources,
        command=search.command_args(),
        timeout_seconds=float(search.timeout_seconds),
    )


def __getattr__(name: str) -> object:
    # Avoid importing FullTextResolver while venue_registry is being imported
    # through the selection/library path. The eager import formed a latent
    # source_resolver <-> library cycle for isolated ranking tests.
    if name == "FullTextResolver":
        from researchsensei.acquisition.fulltext_resolver import FullTextResolver

        return FullTextResolver
    raise AttributeError(name)

__all__ = [
    "ArxivAdapter",
    "OpenAlexAdapter",
    "SemanticScholarAdapter",
    "DBLPAdapter",
    "PaperSearchMcpAdapter",
    "paper_search_mcp_available",
    "make_default_search_adapter",
    "FullTextResolver",
]
