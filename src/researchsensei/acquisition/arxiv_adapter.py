from __future__ import annotations

import arxiv

from researchsensei.schemas import CandidatePaper


class ArxivAdapter:
    """Mature arXiv adapter backed by the `arxiv` Python package."""

    def __init__(self, client: arxiv.Client | None = None) -> None:
        self.client = client or arxiv.Client(page_size=10, delay_seconds=3.0, num_retries=0)

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )
        return [self._to_candidate(result) for result in self.client.results(search)]

    def _to_candidate(self, result) -> CandidatePaper:
        arxiv_id = ""
        if hasattr(result, "get_short_id"):
            arxiv_id = result.get_short_id()
        if not arxiv_id and getattr(result, "entry_id", ""):
            arxiv_id = str(result.entry_id).rstrip("/").rsplit("/", 1)[-1]
        pdf_url = str(getattr(result, "pdf_url", "") or "")
        entry_id = str(getattr(result, "entry_id", "") or "")
        source_url = f"https://arxiv.org/e-print/{arxiv_id}" if arxiv_id else ""
        published = getattr(result, "published", None)
        year = getattr(published, "year", None)
        authors = [getattr(author, "name", str(author)) for author in getattr(result, "authors", [])]
        return CandidatePaper(
            paper_id=arxiv_id or _stable_id(getattr(result, "title", "")),
            title=_clean(getattr(result, "title", "")),
            authors=authors,
            year=year,
            venue="arXiv",
            source="arxiv",
            sources=["arxiv"],
            source_ids={"arxiv": arxiv_id} if arxiv_id else {},
            url=entry_id,
            landing_url=entry_id,
            arxiv_id=arxiv_id,
            abstract=_clean(getattr(result, "summary", "")),
            pdf_url=pdf_url,
            source_url=source_url,
            open_access=bool(pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="high" if arxiv_id else "medium",
            metadata_confidence="medium",
            raw_source_metadata={
                "entry_id": entry_id,
                "updated": str(getattr(result, "updated", "") or ""),
                "published": str(published or ""),
            },
        )


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _stable_id(title: object) -> str:
    return _clean(title).lower().replace(" ", "_")[:60] or "arxiv_unknown"
