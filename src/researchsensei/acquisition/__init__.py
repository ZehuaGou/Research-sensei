"""Acquisition module for paper search adapters."""

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition.dblp_adapter import DBLPAdapter
from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter
from researchsensei.acquisition.paper_search_mcp_adapter import PaperSearchMcpAdapter, paper_search_mcp_available
from researchsensei.acquisition.semantic_scholar_adapter import SemanticScholarAdapter


def make_default_search_adapter() -> PaperSearchMcpAdapter:
    return PaperSearchMcpAdapter()

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
