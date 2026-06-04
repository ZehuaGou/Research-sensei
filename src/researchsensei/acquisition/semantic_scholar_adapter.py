from __future__ import annotations

import os

from semanticscholar import SemanticScholar

from researchsensei.schemas import CandidatePaper


SEMANTIC_SCHOLAR_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "venue",
    "abstract",
    "tldr",
    "citationCount",
    "externalIds",
    "openAccessPdf",
    "url",
]


class SemanticScholarAdapter:
    """Semantic Scholar adapter backed by the real `semanticscholar` package/API."""

    def __init__(self, client: SemanticScholar | None = None, timeout: int = 10) -> None:
        self.client = client or SemanticScholar(
            timeout=timeout,
            api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None,
            retry=False,
        )

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        results = self.client.search_paper(
            query,
            limit=min(max_results, 100),
            fields=SEMANTIC_SCHOLAR_FIELDS,
        )
        return [self._to_candidate(row) for row in list(results)[:max_results] if _get(row, "title")]

    def _to_candidate(self, row) -> CandidatePaper:
        paper_id = str(_get(row, "paperId") or "")
        external_ids = _get(row, "externalIds") or {}
        doi = str(external_ids.get("DOI") or "")
        arxiv_id = str(external_ids.get("ArXiv") or "")
        open_access_pdf = _get(row, "openAccessPdf") or {}
        pdf_url = str(open_access_pdf.get("url") or "")
        tldr = _get(row, "tldr") or {}
        authors = []
        for author in _get(row, "authors") or []:
            name = author.get("name") if isinstance(author, dict) else getattr(author, "name", "")
            if name:
                authors.append(name)
        return CandidatePaper(
            paper_id=paper_id or doi or arxiv_id or _stable_id(_get(row, "title")),
            title=str(_get(row, "title") or ""),
            authors=authors,
            year=_get(row, "year"),
            venue=str(_get(row, "venue") or ""),
            source="semantic_scholar",
            sources=["semantic_scholar"],
            source_ids={"semantic_scholar": paper_id} if paper_id else {},
            url=str(_get(row, "url") or ""),
            landing_url=str(_get(row, "url") or ""),
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=paper_id,
            abstract=str(_get(row, "abstract") or ""),
            tldr=str(tldr.get("text") if isinstance(tldr, dict) else getattr(tldr, "text", "") or ""),
            citation_count=_get(row, "citationCount"),
            pdf_url=pdf_url,
            open_access=bool(pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="high" if paper_id else "medium",
            metadata_confidence="high" if paper_id and (_get(row, "abstract") or tldr) else "medium",
            raw_source_metadata={
                "paperId": paper_id,
                "externalIds": dict(external_ids),
                "openAccessPdf": dict(open_access_pdf),
            },
        )


def _get(row, key: str):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _stable_id(title: object) -> str:
    return "s2_" + "_".join(str(title or "").lower().split())[:50]
