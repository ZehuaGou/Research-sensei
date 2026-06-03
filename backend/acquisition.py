from __future__ import annotations

import xml.etree.ElementTree as ET
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from backend.schemas import CandidatePaper, QueryPlan, SearchRun


class AcquisitionService:
    """Reuse-first acquisition facade.

    It uses public metadata endpoints and optional paper-search-mcp. It never
    falls back to a custom crawler.
    """

    def __init__(self, sources: list[str] | None = None, timeout_seconds: int = 30) -> None:
        self.sources = sources or ["arxiv", "openalex"]
        self.timeout_seconds = timeout_seconds
        # Individual source timeouts (faster)
        self._source_timeout = min(timeout_seconds, 15)

    def search(self, plan: QueryPlan, max_results: int = 20) -> SearchRun:
        candidates = self.collect(plan, max_results=max_results)
        return SearchRun(
            query=plan.direction_en or plan.user_query,
            source_tool="reuse_first",
            api_required=False,
            candidate_papers=candidates,
            search_log=[f"{source}: enabled" for source in self.sources],
        )

    def collect(self, plan: QueryPlan, max_results: int = 20) -> list[CandidatePaper]:
        query = plan.direction_en or plan.user_query
        candidates: list[CandidatePaper] = []

        # Run all sources in parallel for speed
        def _search_source(source: str) -> list[CandidatePaper]:
            try:
                if source == "arxiv":
                    return self._search_arxiv(query, max_results)
                elif source == "openalex":
                    return self._search_openalex(query, max_results)
                elif source in {"google_scholar", "paper-search-mcp"}:
                    return self._search_paper_search_mcp(query, max_results, source)
            except Exception:
                pass
            return []

        with ThreadPoolExecutor(max_workers=len(self.sources)) as executor:
            futures = {executor.submit(_search_source, src): src for src in self.sources}
            for future in as_completed(futures):
                try:
                    candidates.extend(future.result())
                except Exception:
                    pass

        return candidates

    def _search_arxiv(self, query: str, max_results: int) -> list[CandidatePaper]:
        response = httpx.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f'all:"{query}"',
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
            timeout=self._source_timeout,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results: list[CandidatePaper] = []
        for entry in root.findall("atom:entry", ns):
            title = _clean(entry.findtext("atom:title", default="", namespaces=ns))
            summary = _clean(entry.findtext("atom:summary", default="", namespaces=ns))
            url = entry.findtext("atom:id", default="", namespaces=ns)
            published = entry.findtext("atom:published", default="", namespaces=ns)
            arxiv_id = url.rsplit("/", 1)[-1] if url else ""
            results.append(CandidatePaper(
                paper_id=arxiv_id or title.lower().replace(" ", "_")[:40],
                title=title,
                year=int(published[:4]) if published[:4].isdigit() else None,
                venue="arXiv",
                source="arxiv",
                url=url,
                arxiv_id=arxiv_id,
                abstract=summary,
            ))
        return results

    def _search_openalex(self, query: str, max_results: int) -> list[CandidatePaper]:
        response = httpx.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": min(max_results, 50)},
            timeout=self._source_timeout,
        )
        response.raise_for_status()
        results: list[CandidatePaper] = []
        for row in response.json().get("results", []):
            abstract = _openalex_abstract(row.get("abstract_inverted_index") or {})
            results.append(CandidatePaper(
                paper_id=str(row.get("id", "")).rsplit("/", 1)[-1] or str(row.get("doi", "")),
                title=str(row.get("title") or ""),
                year=row.get("publication_year"),
                venue=str(((row.get("primary_location") or {}).get("source") or {}).get("display_name") or ""),
                source="openalex",
                url=str(row.get("id") or ""),
                doi=str(row.get("doi") or ""),
                abstract=abstract,
                citation_count=row.get("cited_by_count"),
            ))
        return [paper for paper in results if paper.title]

    def _search_paper_search_mcp(self, query: str, max_results: int, source: str) -> list[CandidatePaper]:
        script = """
import json, sys
try:
    from paper_search_mcp.server import search_papers
except Exception:
    search_papers = None
query, limit, source = sys.argv[1], int(sys.argv[2]), sys.argv[3]
if search_papers is None:
    print(json.dumps({"results": [], "logs": ["paper-search-mcp import failed"]}))
else:
    rows = search_papers(query=query, limit=limit, source=source)
    print(json.dumps({"results": rows}, ensure_ascii=False))
"""
        result = subprocess.run(
            ["uvx", "--from", "paper-search-mcp", "python", "-c", script, query, str(max_results), source],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            return []
        try:
            payload = json.loads(_extract_json(result.stdout))
        except json.JSONDecodeError:
            return []
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [_paper_from_row(row, source) for row in rows if row.get("title")]


def _clean(value: str) -> str:
    return " ".join((value or "").split())


def _openalex_abstract(inverted: dict) -> str:
    if not inverted:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            positions[int(index)] = word
    return " ".join(positions[index] for index in sorted(positions))


def _extract_json(stdout: str) -> str:
    text = stdout.strip()
    first_obj = text.find("{")
    first_arr = text.find("[")
    starts = [index for index in [first_obj, first_arr] if index >= 0]
    if not starts:
        return text
    return text[min(starts):]


def _paper_from_row(row: dict, source: str) -> CandidatePaper:
    title = str(row.get("title") or row.get("name") or "")
    arxiv_id = str(row.get("arxiv_id") or row.get("arxivId") or "")
    doi = str(row.get("doi") or "")
    return CandidatePaper(
        paper_id=arxiv_id or doi or title.lower().replace(" ", "_")[:48],
        title=title,
        authors=[str(author) for author in row.get("authors", [])] if isinstance(row.get("authors", []), list) else [str(row.get("authors"))],
        year=_int_or_none(row.get("year") or row.get("publication_year")),
        venue=str(row.get("venue") or row.get("journal") or row.get("conference") or source),
        source=source,
        url=str(row.get("url") or row.get("link") or ""),
        doi=doi,
        arxiv_id=arxiv_id,
        abstract=str(row.get("abstract") or row.get("summary") or ""),
        citation_count=_int_or_none(row.get("citation_count") or row.get("citations") or row.get("cited_by_count")),
        pdf_url=str(row.get("pdf_url") or row.get("pdf") or ""),
    )


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None
