from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from researchsensei.acquisition.arxiv_crosslink import ArxivCrosslink
from researchsensei.acquisition.landing_extractor import LandingPdfExtractor, classify_landing_url
from researchsensei.acquisition.pdf_cache import PdfCache
from researchsensei.acquisition.venue_registry import is_known_oa_landing
from researchsensei.schemas import CandidatePaper, SourceStatus
from researchsensei.source_resolver import SourceResolver

logger = logging.getLogger(__name__)

READY_STATUSES = {"source_ready", "pdf_ready", "html_ready"}
PROBE_ONLY_ARCHIVE_KINDS = {"acm_dl", "ieee", "springer", "other", "doi", "repository"}
UNVERIFIED_OFFICIAL_PDF_SOURCE = "official_pdf_url_unverified"
UNVERIFIED_OFFICIAL_PDF_REASON = "PDF_URL_REQUIRES_DOWNLOAD_VERIFICATION"


class FullTextResolver:
    """Discover legal full-text options without pretending metadata is readable.

    Resolver priority:
    1. arXiv source/e-print (LaTeX)
    2. arXiv PDF
    3. OpenAlex/Semantic Scholar OA PDF (best_oa_location.pdf_url, openAccessPdf)
    4. Unpaywall OA PDF
    5. arXiv crosslink: arxiv_id reverse-found in OpenAlex/S2 raw metadata
    6. OA venue landing page -> fetch HTML -> extract PDF URL (landing_extractor)
    7. metadata-only

    PDF cache layer is checked before any HTTP download and populated after
    any successful download, so the same DOI/arxiv_id across directions does
    not re-fetch.
    """

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_download_bytes: int = 80 * 1024 * 1024,
        unpaywall_email: str | None = None,
        landing_extractor: LandingPdfExtractor | None = None,
        arxiv_crosslink: ArxivCrosslink | None = None,
        pdf_cache: PdfCache | None = None,
        cache_root: str | Path | None = None,
    ) -> None:
        default_headers = {
            "User-Agent": "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)",
            "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "close",
        }
        self.http_client = http_client or httpx.Client(
            follow_redirects=True,
            trust_env=True,
            headers=default_headers,
        )
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self.landing_extractor = landing_extractor or LandingPdfExtractor(
            http_client=self.http_client,
            timeout_seconds=timeout_seconds,
        )
        self.arxiv_crosslink = arxiv_crosslink or ArxivCrosslink()
        # PDF cache: explicit instance wins; otherwise construct from env/cache_root.
        self.pdf_cache: PdfCache | None
        if pdf_cache is not None:
            self.pdf_cache = pdf_cache
        else:
            try:
                self.pdf_cache = PdfCache(cache_root=Path(cache_root) if cache_root else None)
            except Exception as exc:  # pragma: no cover - filesystem-unavailable safety
                logger.warning("PDF cache disabled: %s", exc)
                self.pdf_cache = None
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
        arxiv_id = self.arxiv_crosslink.resolve(candidate) or _candidate_arxiv_id(candidate)
        pdf_urls = _unique([*candidate.candidate_pdf_urls, *self._metadata_pdf_urls(candidate, arxiv_id)])
        source_urls = _unique([*candidate.candidate_source_urls, *self._metadata_source_urls(candidate, arxiv_id)])
        html_urls = _unique([*candidate.candidate_html_urls, *self._metadata_html_urls(candidate, arxiv_id)])
        landing_urls = _unique(self._metadata_landing_urls(candidate))

        lookup_errors: list[str] = []
        attempted_landing_urls: set[str] = set()

        def extract_landing_candidates() -> None:
            pending_landing_urls = [url for url in _unique(landing_urls) if url not in attempted_landing_urls]
            attempted_landing_urls.update(pending_landing_urls)
            if not pending_landing_urls:
                return
            extracted_pdfs, landing_metrics, landing_errors = self._extract_oa_landing_pdfs(pending_landing_urls)
            pdf_urls.extend(extracted_pdfs)
            metrics.extend(landing_metrics)
            lookup_errors.extend(landing_errors)

        # Repository copies are frequently listed as secondary OpenAlex
        # locations. Probe them even when the publisher supplied a PDF URL:
        # publisher CDNs may reject server-side downloads while PMC/HAL works.
        repository_landings = [
            url for url in landing_urls if classify_landing_url(url)[1] == "repository"
        ]
        if repository_landings:
            extracted_pdfs, landing_metrics, landing_errors = self._extract_oa_landing_pdfs(repository_landings)
            attempted_landing_urls.update(repository_landings)
            pdf_urls.extend(extracted_pdfs)
            metrics.extend(landing_metrics)
            lookup_errors.extend(landing_errors)

        if not source_urls and not pdf_urls:
            extract_landing_candidates()
            pdf_urls = _unique(pdf_urls)

        if not source_urls and not pdf_urls and candidate.doi:
            started = time.perf_counter()
            unpaywall_pdf, unpaywall_landing, error = self._lookup_unpaywall(candidate.doi)
            metrics.append(_metric("unpaywall", bool(unpaywall_pdf or unpaywall_landing), 1 if (unpaywall_pdf or unpaywall_landing) else 0, started, error))
            if error:
                lookup_errors.append(error)
            if unpaywall_pdf:
                pdf_urls.append(unpaywall_pdf)
            if unpaywall_landing:
                landing_urls.append(unpaywall_landing)
            if _is_fulltext_html_url(unpaywall_landing):
                html_urls.append(unpaywall_landing)
            pdf_urls = _unique(pdf_urls)
            if not source_urls and not pdf_urls:
                extract_landing_candidates()
        elif not source_urls and not pdf_urls and "unpaywall" in (candidate.sources or []):
            metrics.append(_metric("unpaywall", False, 0, time.perf_counter(), "doi_missing"))

        pdf_urls = _unique(pdf_urls)
        source_urls = _unique(source_urls)
        html_urls = _unique(html_urls)

        selected_source, selected_url, status, reason = self._select(candidate, source_urls, pdf_urls, html_urls, arxiv_id=arxiv_id)
        if status == "metadata_only" and lookup_errors:
            reason = ";".join(_unique(lookup_errors))

        # ---- PDF cache short-circuit: avoid HTTP if DOI/arxiv_id already cached ----
        if (
            download
            and status in READY_STATUSES
            and run_dir is not None
            and self.pdf_cache is not None
        ):
            cached_path = self.pdf_cache.get(
                doi=candidate.doi,
                arxiv_id=candidate.arxiv_id or arxiv_id,
                pdf_url=selected_url or (pdf_urls[0] if pdf_urls else ""),
            )
            if cached_path is not None:
                started = time.perf_counter()
                metrics.append(_metric(
                    "pdf_cache",
                    True,
                    1,
                    started,
                    "",
                ))
                # Resolve the cached PDF into the run_dir so downstream paper analysis sees a
                # local file under the expected path layout.
                paper_dir = Path(run_dir) / _safe_name(candidate.paper_id or candidate.title or candidate.doi or "paper")
                paper_dir.mkdir(parents=True, exist_ok=True)
                target = paper_dir / (cached_path.name if cached_path.name.startswith("source.") else "source.pdf")
                try:
                    target.write_bytes(cached_path.read_bytes())
                    run_dir_resolved_fulltext_source = "pdf_cache"
                    run_dir_resolved_url = selected_url or (pdf_urls[0] if pdf_urls else str(cached_path))
                    run_dir_resolved_status = "pdf_ready"
                    run_dir_resolved_reason = "cache_hit"
                    candidate_updates_for_cache_hit = {
                        "pdf_url": candidate.pdf_url or (pdf_urls[0] if pdf_urls else str(cached_path)),
                    }
                    can_deep_read = True
                    needs_user_upload = False
                    updates = {
                        "candidate_pdf_urls": pdf_urls,
                        "candidate_source_urls": source_urls,
                        "candidate_html_urls": html_urls,
                        "arxiv_id": candidate.arxiv_id or arxiv_id,
                        **candidate_updates_for_cache_hit,
                        "selected_fulltext_source": run_dir_resolved_fulltext_source,
                        "selected_fulltext_url": run_dir_resolved_url,
                        "fulltext_status": run_dir_resolved_status,
                        "fulltext_failure_reason": run_dir_resolved_reason,
                        "can_deep_read": can_deep_read,
                        "needs_user_upload": needs_user_upload,
                        "has_valid_deep_reading_source": True,
                        "pdf_available": True,
                        "pdf_downloaded": True,
                        "source_url": candidate.source_url or (source_urls[0] if source_urls else ""),
                        "metadata_only": False,
                    }
                    return candidate.model_copy(update=updates), metrics
                except OSError as exc:
                    logger.warning("PDF cache hit but copy failed: %s; falling back to download", exc)

        download_verified = False
        if download and status in READY_STATUSES and run_dir is not None:
            selected_source, selected_url, status, reason = self._verify_download(
                candidate,
                selected_source=selected_source,
                selected_url=selected_url,
                run_dir=Path(run_dir),
            )
            download_verified = status == "pdf_ready"
            # On successful download, populate the PDF cache so subsequent
            # resolves of the same DOI/arxiv_id short-circuit.
            if (
                self.pdf_cache is not None
                and status == "pdf_ready"
                and selected_url
                and Path(run_dir).exists()
            ):
                try:
                    # Find the downloaded file under run_dir; default to source.pdf
                    paper_dir = Path(run_dir) / _safe_name(candidate.paper_id or candidate.title or candidate.doi or "paper")
                    candidates_pdf_paths = [
                        paper_dir / "source.pdf",
                        paper_dir / "source.tar.gz",
                        paper_dir / "source.tex",
                    ]
                    for cand_path in candidates_pdf_paths:
                        if cand_path.exists():
                            content = cand_path.read_bytes()
                            ext = cand_path.suffix.lstrip(".") or "pdf"
                            self.pdf_cache.put(
                                content,
                                doi=candidate.doi,
                                arxiv_id=candidate.arxiv_id or arxiv_id,
                                pdf_url=selected_url,
                                source_url=source_urls[0] if source_urls else "",
                                venue=candidate.venue,
                                fulltext_source=selected_source or "legal",
                                extension=ext,
                            )
                            break
                except OSError as exc:
                    logger.warning("PDF cache write failed: %s", exc)

        if (
            status == "pdf_ready"
            and not download_verified
            and _requires_download_verification(selected_url)
        ):
            selected_source = UNVERIFIED_OFFICIAL_PDF_SOURCE
            status = "metadata_only"
            reason = UNVERIFIED_OFFICIAL_PDF_REASON

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
        status: SourceStatus | None
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

    def _extract_oa_landing_pdfs(self, landing_urls: list[str]) -> tuple[list[str], list[dict[str, object]], list[str]]:
        pdf_urls: list[str] = []
        metrics: list[dict[str, object]] = []
        errors: list[str] = []
        for landing_url in landing_urls:
            is_oa, archive_kind, cfg = classify_landing_url(landing_url)
            can_probe = archive_kind in PROBE_ONLY_ARCHIVE_KINDS
            if not is_oa and not can_probe:
                continue
            started = time.perf_counter()
            result = self.landing_extractor.extract(landing_url)
            error = ";".join(result.warnings)
            source = f"landing_extractor:{result.archive_kind or archive_kind or (cfg.archive_kind if cfg else '') or 'oa'}"
            metrics.append(_metric(source, bool(result.pdf_url), 1 if result.pdf_url else 0, started, error))
            if result.pdf_url and _is_legal_pdf_url(result.pdf_url):
                pdf_urls.append(result.pdf_url)
            elif error:
                errors.append(f"{archive_kind or 'oa_landing'}:{error}")
        return _unique(pdf_urls), metrics, errors

    def _metadata_pdf_urls(self, candidate: CandidatePaper, arxiv_id: str = "") -> list[str]:
        urls = []
        if candidate.pdf_url:
            urls.append(candidate.pdf_url)
        if arxiv_id:
            urls.append(SourceResolver.arxiv_to_pdf_url(arxiv_id=arxiv_id))
        raw = candidate.raw_source_metadata or {}
        for metadata in _metadata_dicts(raw):
            for key in ("pdf_url", "url_for_pdf"):
                pdf = str(metadata.get(key) or "")
                if pdf:
                    urls.append(pdf)
        for location in _metadata_locations(raw):
            for key in ("pdf_url", "url_for_pdf"):
                pdf = str((location or {}).get(key) or "")
                if pdf:
                    urls.append(pdf)
        for metadata in _metadata_dicts(raw):
            raw_open_access = metadata.get("open_access")
            open_access = raw_open_access if isinstance(raw_open_access, dict) else {}
            oa_url = str(open_access.get("oa_url") or "")
            if _is_legal_pdf_url(oa_url):
                urls.append(oa_url)
            raw_open_access_pdf = metadata.get("openAccessPdf")
            open_access_pdf = raw_open_access_pdf if isinstance(raw_open_access_pdf, dict) else {}
            s2_pdf = str(open_access_pdf.get("url") or "")
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

    def _metadata_landing_urls(self, candidate: CandidatePaper) -> list[str]:
        urls = [
            candidate.landing_url,
            candidate.url,
            *candidate.candidate_html_urls,
        ]
        raw = candidate.raw_source_metadata or {}
        for location in _metadata_locations(raw):
            for key in ("landing_page_url", "url_for_landing_page", "url"):
                urls.append(str((location or {}).get(key) or ""))
        for metadata in _metadata_dicts(raw):
            for key in ("landing_url", "landing_page_url"):
                urls.append(str(metadata.get(key) or ""))
            raw_open_access = metadata.get("open_access")
            open_access = raw_open_access if isinstance(raw_open_access, dict) else {}
            oa_url = str(open_access.get("oa_url") or "")
            if oa_url and not _is_legal_pdf_url(oa_url):
                urls.append(oa_url)
        return _unique([url for url in urls if url])


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
    for location in _metadata_locations(raw):
        values.extend([
            str((location or {}).get("pdf_url") or ""),
            str((location or {}).get("landing_page_url") or ""),
            str((location or {}).get("url") or ""),
        ])
    for value in values:
        arxiv_id = SourceResolver.arxiv_id_from_url(str(value or ""))
        if arxiv_id:
            return arxiv_id
    return ""


def _metadata_locations(raw: dict[str, object]) -> list[dict[str, object]]:
    locations: list[dict[str, object]] = []
    for metadata in _metadata_dicts(raw):
        for key in ("best_oa_location", "primary_location"):
            location = metadata.get(key) if isinstance(metadata.get(key), dict) else None
            if isinstance(location, dict):
                locations.append(location)
        for key in ("locations", "oa_locations"):
            values = metadata.get(key)
            if not isinstance(values, list):
                continue
            locations.extend(location for location in values if isinstance(location, dict))
    return locations


def _metadata_dicts(raw: dict[str, object]) -> list[dict[str, object]]:
    """Return source-specific metadata wrappers produced during deduplication."""

    result: list[dict[str, object]] = []
    pending: list[tuple[dict[str, object], int]] = [(raw, 0)]
    seen: set[int] = set()
    while pending:
        current, depth = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        result.append(current)
        if depth >= 3:
            continue
        for value in current.values():
            if isinstance(value, dict):
                pending.append((value, depth + 1))
    return result


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
    lower = value.lower()
    if lower.endswith(".pdf") or "/pdf" in lower or "pdf" in lower:
        return True
    # OJS-hosted venues such as AAAI often expose PDF files through numeric
    # article/download or article/view galley URLs without a .pdf suffix.
    if "ojs.aaai.org" in lower and re.search(r"/article/(?:download|view)/\d+/\d+", lower):
        return True
    if "ieeexplore.ieee.org/stamp/stamp.jsp" in lower:
        return True
    return False


def _requires_download_verification(url: str) -> bool:
    """Official non-OA publisher PDF URLs are usable only after a real PDF fetch.

    ACM/IEEE/Springer landing pages often expose a /pdf URL even when the file
    may still be gated. Keep the candidate URL so the downloader can try it, but
    do not mark it as deep-readable until the bytes are validated.
    """
    lower = str(url or "").lower()
    if not lower:
        return False
    is_oa, archive_kind, cfg = is_known_oa_landing(lower)
    archive = archive_kind or (cfg.archive_kind if cfg else "")
    if archive in PROBE_ONLY_ARCHIVE_KINDS and not is_oa:
        return True
    return any(
        marker in lower
        for marker in (
            "dl.acm.org/doi/pdf",
            "dl.acm.org/doi/epdf",
            "ieeexplore.ieee.org/stamp/stamp.jsp",
            "link.springer.com/content/pdf",
        )
    )


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
