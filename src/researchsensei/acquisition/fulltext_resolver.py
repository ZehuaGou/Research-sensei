from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from researchsensei.schemas import CandidatePaper
from researchsensei.source_resolver import SourceResolver

READY_STATUSES = {"source_ready", "pdf_ready", "html_ready"}


class FullTextResolver:
    """Discover legal full-text options without pretending metadata is readable.

    Resolver priority:
    arXiv source -> arXiv PDF -> Unpaywall/OpenAlex OA PDF ->
    Semantic Scholar OA PDF -> publisher/repository PDF -> ar5iv/html ->
    user upload / metadata-only.
    """

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_download_bytes: int = 80 * 1024 * 1024,
        unpaywall_email: str | None = None,
    ) -> None:
        self.http_client = http_client or httpx.Client(follow_redirects=True, trust_env=True)
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self.unpaywall_email = (
            unpaywall_email
            if unpaywall_email is not None
            else (os.getenv("UNPAYWALL_EMAIL", "").strip() or os.getenv("RESEARCHSENSEI_CONTACT_EMAIL", "").strip())
        )

    def resolve_many(
        self,
        candidates: list[CandidatePaper],
        *,
        download_top_n: int = 0,
        workspace: str | Path | None = None,
    ) -> tuple[list[CandidatePaper], list[dict[str, object]]]:
        metrics: list[dict[str, object]] = []
        resolved: list[CandidatePaper] = []
        for index, candidate in enumerate(candidates):
            download = index < max(download_top_n, 0)
            run_dir = Path(workspace) / _safe_name(candidate.paper_id or candidate.title) if workspace and download else None
            paper, paper_metrics = self.resolve(candidate, download=download, run_dir=run_dir)
            resolved.append(paper)
            metrics.extend(paper_metrics)
        return resolved, metrics

    def resolve(
        self,
        candidate: CandidatePaper,
        *,
        download: bool = False,
        run_dir: str | Path | None = None,
    ) -> tuple[CandidatePaper, list[dict[str, object]]]:
        metrics: list[dict[str, object]] = []
        arxiv_id = _candidate_arxiv_id(candidate)
        pdf_urls = _unique([*candidate.candidate_pdf_urls, *self._metadata_pdf_urls(candidate, arxiv_id)])
        source_urls = _unique([*candidate.candidate_source_urls, *self._metadata_source_urls(candidate, arxiv_id)])
        html_urls = _unique([*candidate.candidate_html_urls, *self._metadata_html_urls(candidate, arxiv_id)])

        lookup_errors: list[str] = []
        if candidate.doi:
            started = time.perf_counter()
            unpaywall_pdf, unpaywall_landing, error = self._lookup_unpaywall(candidate.doi)
            metrics.append(_metric("unpaywall", bool(unpaywall_pdf or unpaywall_landing), 1 if (unpaywall_pdf or unpaywall_landing) else 0, started, error))
            if error:
                lookup_errors.append(error)
            if unpaywall_pdf:
                pdf_urls.append(unpaywall_pdf)
            if _is_fulltext_html_url(unpaywall_landing):
                html_urls.append(unpaywall_landing)
        elif "unpaywall" in (candidate.sources or []):
            metrics.append(_metric("unpaywall", False, 0, time.perf_counter(), "doi_missing"))

        pdf_urls = _unique(pdf_urls)
        source_urls = _unique(source_urls)
        html_urls = _unique(html_urls)

        selected_source, selected_url, status, reason = self._select(candidate, source_urls, pdf_urls, html_urls, arxiv_id=arxiv_id)
        if status == "metadata_only" and lookup_errors:
            reason = ";".join(_unique(lookup_errors))
        if download and status in READY_STATUSES and run_dir is not None:
            selected_source, selected_url, status, reason = self._verify_download(
                candidate,
                selected_source=selected_source,
                selected_url=selected_url,
                run_dir=Path(run_dir),
            )

        can_deep_read = status in READY_STATUSES
        needs_user_upload = not can_deep_read or status == "metadata_only"
        updates = {
            "candidate_pdf_urls": pdf_urls,
            "candidate_source_urls": source_urls,
            "candidate_html_urls": html_urls,
            "arxiv_id": candidate.arxiv_id or arxiv_id,
            "selected_fulltext_source": selected_source,
            "selected_fulltext_url": selected_url,
            "fulltext_status": status,
            "fulltext_failure_reason": reason,
            "can_deep_read": can_deep_read,
            "needs_user_upload": needs_user_upload,
            "has_valid_deep_reading_source": bool(candidate.has_valid_deep_reading_source or can_deep_read),
            "pdf_available": bool(candidate.pdf_available or pdf_urls),
            "pdf_url": candidate.pdf_url or (pdf_urls[0] if pdf_urls else ""),
            "source_url": candidate.source_url or (source_urls[0] if source_urls else ""),
            "metadata_only": not can_deep_read,
        }
        return candidate.model_copy(update=updates), metrics

    def _lookup_unpaywall(self, doi: str) -> tuple[str, str, str]:
        if not self.unpaywall_email:
            return "", "", "UNPAYWALL_EMAIL_MISSING"
        clean = _normalize_doi(doi)
        if not clean:
            return "", "", "DOI_MISSING"
        try:
            response = self.http_client.get(
                f"https://api.unpaywall.org/v2/{quote(clean, safe='')}",
                params={"email": self.unpaywall_email},
                timeout=self.timeout_seconds,
            )
            if response.status_code == 404:
                return "", "", "UNPAYWALL_NOT_FOUND"
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return "", "", f"{type(exc).__name__}: {str(exc)[:160]}"

        locations = [data.get("best_oa_location") or {}, *(data.get("oa_locations") or [])]
        for location in locations:
            pdf = str(location.get("url_for_pdf") or "")
            landing = str(location.get("url_for_landing_page") or location.get("url") or "")
            if _is_legal_pdf_url(pdf):
                return pdf, landing, ""
        for location in locations:
            landing = str(location.get("url_for_landing_page") or location.get("url") or "")
            if landing:
                return "", landing, ""
        return "", "", "UNPAYWALL_NO_OA_LOCATION"

    def _select(
        self,
        candidate: CandidatePaper,
        source_urls: list[str],
        pdf_urls: list[str],
        html_urls: list[str],
        *,
        arxiv_id: str = "",
    ) -> tuple[str, str, str, str]:
        if arxiv_id:
            source_url = SourceResolver.arxiv_to_source_url(arxiv_id=arxiv_id)
            if source_url:
                return "arxiv_source", source_url, "source_ready", ""
            pdf_url = SourceResolver.arxiv_to_pdf_url(arxiv_id=arxiv_id)
            if pdf_url:
                return "arxiv_pdf", pdf_url, "pdf_ready", ""

        for url in source_urls:
            if "arxiv.org/e-print/" in url:
                return "arxiv_source", url, "source_ready", ""
        for url in pdf_urls:
            if "arxiv.org/pdf/" in url:
                return "arxiv_pdf", url, "pdf_ready", ""
        for url in pdf_urls:
            return _pdf_source_label(url), url, "pdf_ready", ""
        for url in html_urls:
            return _html_source_label(url), url, "html_ready", ""
        return "", "", "metadata_only", _metadata_reason(candidate)

    def _verify_download(
        self,
        candidate: CandidatePaper,
        *,
        selected_source: str,
        selected_url: str,
        run_dir: Path,
    ) -> tuple[str, str, str, str]:
        resolver = SourceResolver(
            http_client=self.http_client,
            timeout_seconds=self.timeout_seconds,
            max_download_bytes=self.max_download_bytes,
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        if selected_source == "arxiv_source" and candidate.arxiv_id:
            status = resolver.resolve_arxiv_id(candidate.arxiv_id, run_dir)
        elif selected_source == "arxiv_source":
            arxiv_id = SourceResolver.arxiv_id_from_url(selected_url)
            status = resolver.resolve_arxiv_id(arxiv_id, run_dir) if arxiv_id else None
        elif selected_source.endswith("_pdf") or selected_source in {"openalex_oa_pdf", "semantic_scholar_oa_pdf", "publisher_oa_pdf", "repository_pdf", "pdf_url"}:
            status = resolver.resolve_pdf_url(selected_url, run_dir)
        else:
            return selected_source, selected_url, "html_ready", ""

        if status is None:
            return selected_source, selected_url, "failed", "SOURCE_RESOLUTION_FAILED"
        if status.status != "resolved":
            return selected_source, selected_url, "failed", ";".join(status.warnings) or status.status
        if status.source_type == "arxiv_source":
            return "arxiv_source", selected_url, "source_ready", ""
        if status.source_type == "arxiv_pdf":
            return "arxiv_pdf", selected_url, "pdf_ready", status.fallback_used
        return selected_source or status.source_type, selected_url, "pdf_ready", ""

    def _metadata_pdf_urls(self, candidate: CandidatePaper, arxiv_id: str = "") -> list[str]:
        urls = []
        if candidate.pdf_url:
            urls.append(candidate.pdf_url)
        if arxiv_id:
            urls.append(SourceResolver.arxiv_to_pdf_url(arxiv_id=arxiv_id))
        raw = candidate.raw_source_metadata or {}
        for key in ("best_oa_location", "primary_location"):
            location = raw.get(key) if isinstance(raw.get(key), dict) else {}
            pdf = str((location or {}).get("pdf_url") or "")
            if pdf:
                urls.append(pdf)
        open_access = raw.get("open_access") if isinstance(raw.get("open_access"), dict) else {}
        oa_url = str((open_access or {}).get("oa_url") or "")
        if _is_legal_pdf_url(oa_url):
            urls.append(oa_url)
        open_access_pdf = raw.get("openAccessPdf") if isinstance(raw.get("openAccessPdf"), dict) else {}
        s2_pdf = str((open_access_pdf or {}).get("url") or "")
        if s2_pdf:
            urls.append(s2_pdf)
        return [url for url in urls if _is_legal_pdf_url(url)]

    def _metadata_source_urls(self, candidate: CandidatePaper, arxiv_id: str = "") -> list[str]:
        urls = []
        if candidate.source_url:
            urls.append(candidate.source_url)
        if arxiv_id:
            urls.append(SourceResolver.arxiv_to_source_url(arxiv_id=arxiv_id))
        return [url for url in urls if url]

    def _metadata_html_urls(self, candidate: CandidatePaper, arxiv_id: str = "") -> list[str]:
        urls = []
        if arxiv_id:
            urls.append(f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}")
        return _unique([url for url in urls if _is_fulltext_html_url(url)])


def _metric(source: str, success: bool, count: int, started: float, error: str) -> dict[str, object]:
    return {
        "source": source,
        "attempted": True,
        "success": success,
        "count": count,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "error": error,
    }


def _metadata_reason(candidate: CandidatePaper) -> str:
    if candidate.doi:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    return "NO_ARXIV_OR_OA_PDF_URL"


def _candidate_arxiv_id(candidate: CandidatePaper) -> str:
    if candidate.arxiv_id:
        return candidate.arxiv_id
    values = [
        candidate.source_url,
        candidate.pdf_url,
        candidate.landing_url,
        candidate.url,
        *candidate.candidate_source_urls,
        *candidate.candidate_pdf_urls,
        *candidate.candidate_html_urls,
    ]
    raw = candidate.raw_source_metadata or {}
    for key in ("best_oa_location", "primary_location"):
        location = raw.get(key) if isinstance(raw.get(key), dict) else {}
        values.extend([
            str((location or {}).get("pdf_url") or ""),
            str((location or {}).get("landing_page_url") or ""),
        ])
    for value in values:
        arxiv_id = SourceResolver.arxiv_id_from_url(str(value or ""))
        if arxiv_id:
            return arxiv_id
    return ""


def _normalize_doi(doi: str) -> str:
    clean = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    return clean


def _is_legal_pdf_url(url: str) -> bool:
    value = str(url or "").strip()
    if not value.lower().startswith(("http://", "https://")):
        return False
    return value.lower().endswith(".pdf") or "/pdf" in value.lower() or "pdf" in value.lower()


def _pdf_source_label(url: str) -> str:
    lower = url.lower()
    if "semanticscholar" in lower or "s2orc" in lower:
        return "semantic_scholar_oa_pdf"
    if "arxiv.org/pdf/" in lower:
        return "arxiv_pdf"
    if any(term in lower for term in ("institution", "repository", "eprints", "escholarship", "hal.science", "zenodo")):
        return "repository_pdf"
    return "openalex_oa_pdf" if "openalex" in lower else "publisher_oa_pdf"


def _html_source_label(url: str) -> str:
    return "ar5iv_html" if "ar5iv.labs.arxiv.org" in url.lower() else "landing_html"


def _is_fulltext_html_url(url: str) -> bool:
    lower = str(url or "").lower()
    return "ar5iv.labs.arxiv.org/html/" in lower


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "paper"
