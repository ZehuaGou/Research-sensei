"""Acquisition module for paper search adapters."""

from researchsensei.acquisition.arxiv_adapter import ArxivAdapter
from researchsensei.acquisition.openalex_adapter import OpenAlexAdapter

__all__ = ["ArxivAdapter", "OpenAlexAdapter"]
