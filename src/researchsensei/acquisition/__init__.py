"""Acquisition module for paper search adapters."""

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition.crossref_adapter import CrossrefAdapter
from researchsensei.acquisition.dblp_adapter import DBLPAdapter
from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter
from researchsensei.acquisition.semantic_scholar_adapter import SemanticScholarAdapter

__all__ = [
    "ArxivAdapter",
    "OpenAlexAdapter",
    "SemanticScholarAdapter",
    "CrossrefAdapter",
    "DBLPAdapter",
    "FullTextResolver",
]
