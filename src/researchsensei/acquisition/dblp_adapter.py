from __future__ import annotations

import re

import httpx

from researchsensei.schemas import CandidatePaper

_DBLP_API = "https://dblp.org/search/publ/api"


class DBLPAdapter:
    """DBLP publication search adapter.

    DBLP is metadata-only for this project: it improves CS venue discovery but
    does not grant full text access. DOI/arXiv links discovered in DBLP are
    passed to the full-text resolver.
    """

    def __init__(self, *, timeout: float = 15.0, http_client: httpx.Client | None = None) -> None:
        self.timeout = timeout
        self.http_client = http_client or httpx.Client(timeout=timeout, follow_redirects=True, trust_env=True)

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        response = self.http_client.get(
            _DBLP_API,
            params={"q": query, "format": "json", "h": min(max_results, 100)},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        hits = (((data.get("result") or {}).get("hits") or {}).get("hit") or [])[:max_results]
        return [self._to_candidate(hit) for hit in hits if ((hit.get("info") or {}).get("title"))]

    def _to_candidate(self, hit: dict) -> CandidatePaper:
        info = hit.get("info") or {}
        title = _clean_title(info.get("title"))
        doi = _doi_from_info(info)
        url = str(info.get("url") or "")
        ee = _first(info.get("ee"))
        arxiv_id = _arxiv_id_from_text(" ".join([url, ee]))
        authors = _authors(info.get("authors"))
        paper_id = doi or arxiv_id or str(info.get("key") or "") or _stable_id(title)
        landing_url = ee or url
        return CandidatePaper(
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=_int_or_none(info.get("year")),
            venue=str(info.get("venue") or ""),
            source="dblp",
            sources=["dblp"],
            source_ids={"dblp": str(info.get("key") or paper_id)},
            url=url,
            landing_url=landing_url,
            doi=doi,
            arxiv_id=arxiv_id,
            pdf_url=_pdf_url_from_text(ee),
            open_access=bool(arxiv_id or _pdf_url_from_text(ee)),
            pdf_available=bool(_pdf_url_from_text(ee)),
            source_confidence="medium" if paper_id else "low",
            metadata_confidence="medium" if title and (doi or arxiv_id or url) else "low",
            raw_source_metadata={
                "key": info.get("key"),
                "type": info.get("type"),
                "ee": ee,
                "url": url,
                "note": "DBLP is used as metadata discovery only; full text must be resolved legally elsewhere.",
            },
        )


def _authors(raw: object) -> list[str]:
    author_obj = (raw or {}).get("author") if isinstance(raw, dict) else raw
    if isinstance(author_obj, list):
        return [str((item or {}).get("text") if isinstance(item, dict) else item) for item in author_obj if item]
    if isinstance(author_obj, dict):
        value = author_obj.get("text") or author_obj.get("@pid") or ""
        return [str(value)] if value else []
    if author_obj:
        return [str(author_obj)]
    return []


def _first(value: object) -> str:
    if isinstance(value, list):
        return _first(value[0]) if value else ""
    if isinstance(value, dict):
        return str(value.get("text") or value.get("@href") or value.get("href") or "")
    return str(value or "")


def _doi_from_info(info: dict) -> str:
    for value in (info.get("doi"), info.get("ee"), info.get("url")):
        text = _first(value)
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
        if match:
            return match.group(0).rstrip(".")
    return ""


def _arxiv_id_from_text(text: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", text, re.I)
    return match.group(1) if match else ""


def _pdf_url_from_text(text: str) -> str:
    value = str(text or "")
    return value if value.lower().endswith(".pdf") or "/pdf/" in value.lower() else ""


def _clean_title(title: object) -> str:
    return re.sub(r"\s+", " ", str(title or "").replace("<sub>", "").replace("</sub>", "")).strip().rstrip(".")


def _int_or_none(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _stable_id(title: str) -> str:
    return "dblp_" + "_".join(title.lower().split())[:50]
