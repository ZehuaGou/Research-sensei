from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from ast import literal_eval
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from researchsensei.schemas import CandidatePaper

DEFAULT_PAPER_SEARCH_SOURCES = "openalex,semantic,crossref,dblp,arxiv,core"


class PaperSearchMcpAdapter:
    """ResearchSensei adapter over the external `paper-search-mcp` CLI."""

    def __init__(
        self,
        *,
        sources: str | Sequence[str] | None = None,
        command: Sequence[str] | None = None,
        timeout_seconds: float = 90.0,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        self.sources = _normalize_sources(sources or os.getenv("RESEARCHSENSEI_PAPER_SEARCH_SOURCES", "") or DEFAULT_PAPER_SEARCH_SOURCES)
        self.command = list(command) if command is not None else _default_command()
        self.timeout_seconds = timeout_seconds
        self.runner = runner or subprocess.run
        self.cwd = str(cwd) if cwd is not None else None

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        clean_query = " ".join(query.split())
        if not clean_query:
            return []
        payload = self._run_search(clean_query, max_results=max_results)
        papers = payload.get("papers", [])
        if not isinstance(papers, list):
            raise RuntimeError("paper-search-mcp returned invalid JSON: `papers` is not a list")
        return [
            self._to_candidate(row, rank=index)
            for index, row in enumerate(papers, 1)
            if isinstance(row, dict) and str(row.get("title") or "").strip()
        ]

    def _run_search(self, query: str, *, max_results: int) -> dict[str, Any]:
        args = [
            *self.command,
            "search",
            query,
            "--max-results",
            str(max(max_results, 1)),
            "--sources",
            ",".join(self.sources),
        ]
        try:
            completed = self.runner(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.cwd,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "paper-search-mcp CLI is not installed. Install project dependencies, or set "
                "RESEARCHSENSEI_PAPER_SEARCH_COMMAND to a working paper-search command."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"paper-search-mcp timed out after {self.timeout_seconds:.0f}s") from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            message = _compact_text(stderr or stdout)
            raise RuntimeError(f"paper-search-mcp search failed: {message[:240]}")
        try:
            payload = json.loads(_json_object_text(stdout))
        except Exception as exc:
            message = _compact_text(stdout or stderr)
            raise RuntimeError(f"paper-search-mcp returned non-JSON output: {message[:240]}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("paper-search-mcp returned invalid JSON: root is not an object")
        return payload

    def _to_candidate(self, row: dict[str, Any], *, rank: int) -> CandidatePaper:
        title = _clean_title(str(row.get("title") or ""))
        source = str(row.get("source") or "paper_search").strip() or "paper_search"
        paper_id = str(row.get("paper_id") or "").strip()
        doi = _clean_doi(str(row.get("doi") or ""))
        url = str(row.get("url") or "").strip()
        raw_pdf_url = str(row.get("pdf_url") or "").strip()
        pdf_url = raw_pdf_url if _looks_like_pdf_url(raw_pdf_url) else ""
        published_date = str(row.get("published_date") or "").strip()
        year = _year_from_date(published_date)
        authors = _split_semicolon_field(row.get("authors"))
        categories = _split_semicolon_field(row.get("categories"))
        venue = _venue_from_extra(row.get("extra"))
        citation_count = _int_value(row.get("citations"))
        arxiv_id = _arxiv_id_from_text(url) or _arxiv_id_from_text(pdf_url)
        stable = _stable_id(title)
        external_id = paper_id or doi or stable
        candidate_pdf_urls = [pdf_url] if pdf_url else []
        candidate_html_urls = [value for value in [url, raw_pdf_url] if value and value not in candidate_pdf_urls]

        return CandidatePaper(
            paper_id=f"paper_search_{source}_{stable}",
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            source=source,
            sources=_unique(["paper_search_mcp", source]),
            source_ids={source: external_id, "paper_search_mcp": external_id},
            url=url,
            landing_url=url,
            doi=doi,
            arxiv_id=arxiv_id,
            abstract=str(row.get("abstract") or "").strip(),
            citation_count=citation_count,
            pdf_url=pdf_url,
            candidate_pdf_urls=candidate_pdf_urls,
            candidate_html_urls=candidate_html_urls,
            open_access=bool(pdf_url or arxiv_id),
            pdf_available=bool(pdf_url),
            source_confidence="high" if source in {"openalex", "semantic", "arxiv", "dblp"} else "medium",
            metadata_confidence="high" if title and (authors or doi or paper_id) else "medium",
            raw_source_metadata={
                "rank": rank,
                "provider": "paper-search-mcp",
                "paper_search_source": source,
                "paper_search_sources": list(self.sources),
                "categories": categories,
                "keywords": _split_semicolon_field(row.get("keywords")),
                "raw_result": dict(row),
            },
        )


def paper_search_mcp_available() -> bool:
    command = _default_command()
    try:
        completed = subprocess.run(
            [*command, "sources"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return False
    return completed.returncode == 0


def _default_command() -> list[str]:
    configured = os.getenv("RESEARCHSENSEI_PAPER_SEARCH_COMMAND", "").strip()
    if configured:
        return _split_command(configured)
    if _python_can_import_paper_search(sys.executable):
        return [sys.executable, "-m", "paper_search_mcp.cli"]
    venv_python = _project_venv_python()
    if venv_python and _python_can_import_paper_search(str(venv_python)):
        return [str(venv_python), "-m", "paper_search_mcp.cli"]
    return [sys.executable, "-m", "paper_search_mcp.cli"]


def _project_venv_python() -> Path | None:
    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _python_can_import_paper_search(python_executable: str) -> bool:
    try:
        completed = subprocess.run(
            [python_executable, "-c", "import paper_search_mcp.cli"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return False
    return completed.returncode == 0


def _split_command(command: str) -> list[str]:
    return [part for part in re.findall(r'"([^"]+)"|(\S+)', command) for part in part if part]


def _normalize_sources(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, str):
        parts = value.split(",")
    else:
        parts = list(value)
    result: list[str] = []
    for part in parts:
        source = str(part or "").strip().lower()
        if source and source not in result:
            result.append(source)
    return result or DEFAULT_PAPER_SEARCH_SOURCES.split(",")


def _split_semicolon_field(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def _clean_doi(value: str) -> str:
    return value.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")


def _arxiv_id_from_text(text: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", str(text or ""), re.I)
    return match.group(1) if match else ""


def _stable_id(title: str) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", str(title or "").lower()))[:80] or "unknown"


def _clean_title(value: str) -> str:
    title = " ".join(str(value or "").split())
    while True:
        cleaned = re.sub(r"^\[[^\]]+\]\s*", "", title).strip()
        if cleaned == title:
            return title
        title = cleaned


def _year_from_date(value: str) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", value)
    if match:
        return int(match.group(0))
    try:
        return datetime.fromisoformat(value).year
    except ValueError:
        return None


def _venue_from_extra(extra: object) -> str:
    if isinstance(extra, str) and extra.strip().startswith("{"):
        try:
            extra = literal_eval(extra)
        except (ValueError, SyntaxError):
            pass
    if isinstance(extra, dict):
        for key in ("venue", "journal", "container_title", "publication_venue"):
            value = str(extra.get(key) or "").strip()
            if value:
                return value
    return ""


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value or "").replace(",", "").strip()
    if text.isdigit():
        return int(text)
    return None


def _looks_like_pdf_url(value: str) -> bool:
    lower = str(value or "").lower()
    if not lower.startswith(("http://", "https://")):
        return False
    if lower.endswith(".pdf") or "/pdf" in lower:
        return True
    if "ojs.aaai.org" in lower and re.search(r"/article/(?:download|view)/\d+/\d+", lower):
        return True
    if "ieeexplore.ieee.org" in lower and ("/stamp/" in lower or "/ielx" in lower):
        return True
    return False


def _json_object_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _compact_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
