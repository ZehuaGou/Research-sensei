from __future__ import annotations

from habanero import Crossref

from researchsensei.schemas import CandidatePaper


class CrossrefAdapter:
    """Crossref adapter backed by `habanero.Crossref`."""

    def __init__(self, client: Crossref | None = None) -> None:
        self.client = client or Crossref()

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        response = self.client.works(query=query, limit=min(max_results, 100))
        rows = ((response.get("message") or {}).get("items") or [])[:max_results]
        return [self._to_candidate(row) for row in rows if row.get("title")]

    def _to_candidate(self, row: dict) -> CandidatePaper:
        title = _first(row.get("title"))
        doi = str(row.get("DOI") or "")
        authors = []
        for author in row.get("author") or []:
            name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
            if name:
                authors.append(name)
        year = _year(row)
        venue = _first(row.get("container-title"))
        url = str(row.get("URL") or "")
        pdf_url = _pdf_url(row)
        return CandidatePaper(
            paper_id=doi or url or _stable_id(title),
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            source="crossref",
            sources=["crossref"],
            source_ids={"crossref": doi} if doi else {},
            url=url,
            landing_url=url,
            doi=doi,
            pdf_url=pdf_url,
            abstract=str(row.get("abstract") or ""),
            open_access=bool(pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="medium" if doi else "low",
            metadata_confidence="medium" if doi and title else "low",
            raw_source_metadata={
                "DOI": doi,
                "URL": url,
                "type": row.get("type"),
                "publisher": row.get("publisher"),
                "is-referenced-by-count": row.get("is-referenced-by-count"),
                "link": row.get("link") or [],
            },
        )


def _first(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _year(row: dict) -> int | None:
    for key in ("published-print", "published-online", "issued"):
        parts = ((row.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                return None
    return None


def _pdf_url(row: dict) -> str:
    for link in row.get("link") or []:
        if not isinstance(link, dict):
            continue
        url = str(link.get("URL") or "")
        content_type = str(link.get("content-type") or "")
        if url and ("pdf" in content_type.lower() or url.lower().endswith(".pdf")):
            return url
    return ""


def _stable_id(title: str) -> str:
    return "crossref_" + "_".join(title.lower().split())[:50]
