from __future__ import annotations

import logging

import httpx

from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

OPENALEX_API_URL = "https://api.openalex.org/works"


class OpenAlexAdapter:
    """Adapter for searching papers via the OpenAlex API."""

    def __init__(self, http_client: httpx.Client | None = None, timeout: float = 15.0) -> None:
        self.http_client = http_client or httpx.Client()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        """Search OpenAlex for papers matching the query."""
        try:
            response = self.http_client.get(
                OPENALEX_API_URL,
                params={"search": query, "per-page": min(max_results, 50)},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_response(response.json())
        except Exception as exc:
            logger.warning("OpenAlex search failed for '%s': %s", query, exc)
            raise

    def _parse_response(self, data: dict) -> list[CandidatePaper]:
        """Parse OpenAlex JSON response into CandidatePaper objects."""
        results: list[CandidatePaper] = []
        for row in data.get("results", []):
            abstract = _openalex_abstract(row.get("abstract_inverted_index") or {})
            title = str(row.get("title") or "")

            if not title:
                continue

            # Extract authors
            authors = []
            for authorship in row.get("authorships", []):
                author = authorship.get("author", {})
                if author.get("display_name"):
                    authors.append(author["display_name"])

            # Extract venue
            venue = ""
            primary_location = row.get("primary_location") or {}
            source = primary_location.get("source") or {}
            if source.get("display_name"):
                venue = source["display_name"]

            results.append(CandidatePaper(
                paper_id=str(row.get("id", "")).rsplit("/", 1)[-1] or str(row.get("doi", "")),
                title=title,
                authors=authors,
                year=row.get("publication_year"),
                venue=venue,
                source="openalex",
                url=str(row.get("id") or ""),
                doi=str(row.get("doi") or ""),
                abstract=abstract,
                citation_count=row.get("cited_by_count"),
            ))

        return results


def _openalex_abstract(inverted: dict) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted:
        return ""
    try:
        positions: dict[int, str] = {}
        for word, indexes in inverted.items():
            for index in indexes:
                positions[int(index)] = word
        return " ".join(positions[index] for index in sorted(positions))
    except (KeyError, ValueError, TypeError):
        return ""
