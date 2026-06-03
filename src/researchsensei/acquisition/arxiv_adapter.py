from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivAdapter:
    """Adapter for searching papers via the arXiv API."""

    def __init__(self, http_client: httpx.Client | None = None, timeout: float = 15.0) -> None:
        self.http_client = http_client or httpx.Client()
        self.timeout = timeout

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        """Search arXiv for papers matching the query."""
        try:
            response = self.http_client.get(
                ARXIV_API_URL,
                params={
                    "search_query": f'all:"{query}"',
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse_response(response.text)
        except Exception as exc:
            logger.warning("arXiv search failed for '%s': %s", query, exc)
            raise

    def _parse_response(self, xml_text: str) -> list[CandidatePaper]:
        """Parse arXiv Atom XML response into CandidatePaper objects."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("Failed to parse arXiv XML: %s", exc)
            return []

        results: list[CandidatePaper] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            title = _clean(entry.findtext("atom:title", default="", namespaces=ARXIV_NS))
            summary = _clean(entry.findtext("atom:summary", default="", namespaces=ARXIV_NS))
            url = entry.findtext("atom:id", default="", namespaces=ARXIV_NS)
            published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
            arxiv_id = url.rsplit("/", 1)[-1] if url else ""

            # Extract authors
            authors = []
            for author_elem in entry.findall("atom:author", ARXIV_NS):
                name = author_elem.findtext("atom:name", default="", namespaces=ARXIV_NS)
                if name:
                    authors.append(name)

            # Extract PDF link
            pdf_url = ""
            for link_elem in entry.findall("atom:link", ARXIV_NS):
                if link_elem.get("title") == "pdf":
                    pdf_url = link_elem.get("href", "")
                    break

            if title:
                results.append(CandidatePaper(
                    paper_id=arxiv_id or title.lower().replace(" ", "_")[:40],
                    title=title,
                    authors=authors,
                    year=int(published[:4]) if published[:4].isdigit() else None,
                    venue="arXiv",
                    source="arxiv",
                    url=url,
                    arxiv_id=arxiv_id,
                    abstract=summary,
                    pdf_url=pdf_url,
                ))

        return results


def _clean(value: str) -> str:
    """Clean whitespace from text."""
    return " ".join((value or "").split())
