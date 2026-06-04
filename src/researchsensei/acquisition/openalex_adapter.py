from __future__ import annotations

from pyalex import Works

from researchsensei.schemas import CandidatePaper


class OpenAlexAdapter:
    """Mature OpenAlex adapter backed by `pyalex.Works`."""

    def __init__(self, works: Works | None = None) -> None:
        self.works = works or Works()

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        rows = self.works.search(query).get(per_page=min(max_results, 50))
        return [self._to_candidate(row) for row in rows if row.get("title")]

    def _to_candidate(self, row: dict) -> CandidatePaper:
        work_id = str(row.get("id") or "")
        doi = str(row.get("doi") or "")
        primary_location = row.get("primary_location") or {}
        best_oa_location = row.get("best_oa_location") or {}
        open_access = row.get("open_access") or {}
        landing_url = (
            best_oa_location.get("landing_page_url")
            or primary_location.get("landing_page_url")
            or work_id
        )
        pdf_url = best_oa_location.get("pdf_url") or primary_location.get("pdf_url") or ""
        source = primary_location.get("source") or {}
        authors = []
        for authorship in row.get("authorships", []):
            author = authorship.get("author") or {}
            if author.get("display_name"):
                authors.append(author["display_name"])
        paper_id = work_id.rstrip("/").rsplit("/", 1)[-1] or doi or _stable_id(row.get("title", ""))
        return CandidatePaper(
            paper_id=paper_id,
            title=str(row.get("title") or ""),
            authors=authors,
            year=row.get("publication_year"),
            venue=str(source.get("display_name") or ""),
            source="openalex",
            sources=["openalex"],
            source_ids={"openalex": paper_id},
            url=work_id,
            landing_url=str(landing_url or ""),
            doi=doi,
            abstract=_openalex_abstract(row.get("abstract_inverted_index") or {}),
            citation_count=row.get("cited_by_count"),
            pdf_url=str(pdf_url or ""),
            open_access=bool((open_access or {}).get("is_oa") or pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="high" if work_id else "medium",
            metadata_confidence=_metadata_confidence(row, pdf_url),
            raw_source_metadata={
                "id": work_id,
                "doi": doi,
                "primary_location": _location_summary(primary_location),
                "best_oa_location": _location_summary(best_oa_location),
                "open_access": {
                    "is_oa": (open_access or {}).get("is_oa"),
                    "oa_status": (open_access or {}).get("oa_status"),
                    "oa_url": (open_access or {}).get("oa_url"),
                },
            },
        )


def _openalex_abstract(inverted: dict) -> str:
    if not inverted:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            positions[int(index)] = word
    return " ".join(positions[index] for index in sorted(positions))


def _location_summary(location: dict) -> dict[str, object]:
    return {
        "pdf_url": location.get("pdf_url"),
        "landing_page_url": location.get("landing_page_url"),
        "is_oa": location.get("is_oa"),
        "source": (location.get("source") or {}).get("display_name"),
    }


def _metadata_confidence(row: dict, pdf_url: str) -> str:
    fields = [
        row.get("title"),
        row.get("publication_year"),
        row.get("doi"),
        row.get("abstract_inverted_index"),
        row.get("cited_by_count") is not None,
        pdf_url,
    ]
    filled = sum(1 for value in fields if value)
    if filled >= 5:
        return "high"
    if filled >= 3:
        return "medium"
    return "low"


def _stable_id(title: object) -> str:
    return "openalex_" + "_".join(str(title or "").lower().split())[:50]
