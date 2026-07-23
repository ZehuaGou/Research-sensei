from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

from researchsensei.browser_downloader import BrowserDownloadResult, BrowserSessionDownloader
from researchsensei.library import PaperLibraryRecord, PaperLibraryStore
from researchsensei.schemas import (
    CandidatePaper,
    PaperSourceStatus,
    PaperSourceType,
    ResolvedPaperSource,
    SourcePriority,
    SourceResolutionResult,
    SourceStatus,
    WarningItem,
)

logger = logging.getLogger(__name__)

SUPPORTED_LOCAL_SUFFIXES = {".md", ".txt", ".pdf", ".tex"}
PDF_BYTES = b"%PDF"
GZIP_BYTES = b"\x1f\x8b"
PMC_CLOUD_BASE_URL = "https://pmc-oa-opendata.s3.amazonaws.com"
PMC_ID_CONVERTER_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
BROWSER_METADATA_HOSTS = {
    "api.openalex.org",
    "crossref.org",
    "dblp.org",
    "doi.org",
    "openalex.org",
    "semanticscholar.org",
    "www.crossref.org",
    "www.dblp.org",
    "www.doi.org",
    "www.openalex.org",
    "www.semanticscholar.org",
}
BROWSER_DOI_DISCOVERY_HOSTS = {
    # Live-verified: DOI-only ACM pages can expose a downloadable PDF after
    # their transient security check and full page hydration complete.
    "dl.acm.org",
}


@dataclass(frozen=True)
class LatexSourceMaterialization:
    main_tex: Path | None
    selection_reason: str
    extracted_files: list[Path]
    warnings: list[str]


class PaperSourceResolver:
    """M1 resolver for candidate-paper source acquisition.

    M1 must distinguish metadata-only candidates from papers whose full-text PDF
    was actually downloaded and validated. Parsing still belongs to M2.
    """

    def __init__(
        self,
        *,
        network_enabled: bool = False,
        download_dir: str | Path | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_download_bytes: int = 80 * 1024 * 1024,
        external_resolver: Callable[[CandidatePaper], ResolvedPaperSource | None] | None = None,
        paper_library: PaperLibraryStore | None = None,
        browser_downloader: BrowserSessionDownloader | None = None,
    ) -> None:
        self.network_enabled = network_enabled
        self.download_dir = Path(download_dir).resolve() if download_dir else None
        _default_headers = {"User-Agent": "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"}
        if http_client:
            self.http_client = http_client
        else:
            self.http_client = httpx.Client(headers=_default_headers, trust_env=True)
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self.external_resolver = external_resolver
        self.paper_library = paper_library
        self.browser_downloader = browser_downloader

    def resolve_many(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        download_dir: str | Path | None = None,
    ) -> SourceResolutionResult:
        actual_download_dir = Path(download_dir).resolve() if download_dir else self.download_dir
        items = [self.resolve_one(candidate, download_dir=actual_download_dir) for candidate in candidates]
        if actual_download_dir is not None:
            self._write_search_manifest(actual_download_dir, query, candidates, items)
        if self.paper_library is not None:
            self.paper_library.record_search(
                query=query,
                candidates=candidates,
                items=items,
                topic_folder=str(actual_download_dir or ""),
            )
        warnings: list[WarningItem] = []
        if any(not item.has_valid_deep_reading_source for item in items):
            warnings.append(
                WarningItem(
                    code="PARTIAL_SOURCE_RESOLUTION",
                    message="Some candidates were not resolved to validated full-text sources.",
                )
            )
        return SourceResolutionResult(query=query, items=items, warnings=warnings)

    def resolve_one(
        self,
        paper: CandidatePaper,
        *,
        download_dir: str | Path | None = None,
    ) -> ResolvedPaperSource:
        if self.paper_library is not None:
            cached = self.paper_library.find_match(paper)
            if cached is not None:
                return self._library_reuse_result(paper, cached)

        try:
            if self.network_enabled and self.external_resolver is not None:
                resolved = self.external_resolver(paper)
                if resolved is not None:
                    return resolved
        except Exception as exc:
            logger.warning("M1 paper source resolver failed for %s: %s", paper.paper_id, exc)
            return self._base_result(
                paper,
                status=PaperSourceStatus.FAILED_DOWNLOAD,
                source_type=PaperSourceType.METADATA_ONLY,
                warnings=[WarningItem(code="RESOLVER_FAILED", message="External source resolver failed.")],
                error=str(exc)[:300],
                error_code="RESOLVER_FAILED",
            )

        source_url = ""
        pdf_urls = _ordered_pdf_urls(
            [paper.pdf_url, paper.selected_fulltext_url, *paper.candidate_pdf_urls]
        )
        pdf_url = pdf_urls[0] if pdf_urls else ""
        landing_url = paper.landing_url or paper.url or _doi_url(paper.doi)
        source_type = PaperSourceType.PDF if pdf_url else PaperSourceType.METADATA_ONLY

        if paper.arxiv_id:
            arxiv_pdf = SourceResolver.arxiv_to_pdf_url(arxiv_id=paper.arxiv_id)
            pdf_url = pdf_url or arxiv_pdf
            pdf_urls = _ordered_pdf_urls([pdf_url, *pdf_urls])
            source_url = self.arxiv_to_source_url(paper.arxiv_id)
            landing_url = landing_url or self.arxiv_to_abs_url(paper.arxiv_id)
            source_type = PaperSourceType.ARXIV_SOURCE
            if self.network_enabled and (download_dir or self.download_dir):
                source_result = self._download_arxiv_source_result(
                    paper,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    landing_url=landing_url,
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                )
                if source_result is not None:
                    if source_result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED:
                        return source_result
                    pdf_result = self._download_pdf(
                        paper,
                        pdf_url=pdf_url,
                        source_url=source_url,
                        landing_url=landing_url,
                        source_type=PaperSourceType.PDF,
                        download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                    )
                    if pdf_result.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED:
                        return pdf_result.model_copy(
                            update={
                                "warnings": [*source_result.warnings, *pdf_result.warnings],
                                "metadata": {
                                    **source_result.metadata,
                                    **pdf_result.metadata,
                                    "resolution_strategy": "arxiv_source_plus_pdf",
                                    "latex_source_retained": "true",
                                },
                                "source_priority": SourcePriority.PDF,
                                "preferred_m2_input": "pdf",
                                "has_valid_deep_reading_source": True,
                                "latex_source_available": source_result.latex_source_available,
                                "latex_source_downloaded": source_result.latex_source_downloaded,
                                "latex_main_file": source_result.latex_main_file,
                                "latex_source_path": source_result.latex_source_path,
                            }
                        )
                    return source_result.model_copy(
                        update={
                            "warnings": [
                                *source_result.warnings,
                                WarningItem(
                                    code="PAPER_AGENT_PDF_UNAVAILABLE",
                                    message="LaTeX source was retained, but no validated PDF is available for the paper agent.",
                                ),
                            ],
                            "metadata": {
                                **source_result.metadata,
                                "pdf_download_error": pdf_result.error or pdf_result.error_code,
                            },
                        }
                    )
                source_type = PaperSourceType.PDF

        pmcid = _paper_pmcid(paper)
        if pmcid and self.network_enabled and (download_dir or self.download_dir):
            pmc_result = self._download_pmc_cloud_pdf(
                paper,
                pmcid=pmcid,
                landing_url=landing_url,
                download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
            )
            if pmc_result is not None:
                return pmc_result

        if pdf_url:
            if self.network_enabled and (download_dir or self.download_dir):
                failures: list[ResolvedPaperSource] = []
                for candidate_pdf_url in pdf_urls:
                    attempt = self._download_pdf(
                        paper,
                        pdf_url=candidate_pdf_url,
                        source_url=source_url or candidate_pdf_url,
                        landing_url=landing_url,
                        source_type=source_type,
                        download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                    )
                    if attempt.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED:
                        if failures:
                            attempt = attempt.model_copy(
                                update={
                                    "metadata": {
                                        **attempt.metadata,
                                        "attempted_pdf_urls": [item.pdf_url for item in failures] + [candidate_pdf_url],
                                        "fallback_count": len(failures),
                                    }
                                }
                            )
                        return attempt
                    failures.append(attempt)
                last_failure = failures[-1]
                pmc_result = self._download_pmc_pdf_for_doi(
                    paper,
                    landing_url=landing_url,
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                )
                if pmc_result is not None:
                    return pmc_result.model_copy(
                        update={
                            "metadata": {
                                **pmc_result.metadata,
                                "attempted_pdf_urls": [item.pdf_url for item in failures],
                                "fallback_count": len(failures),
                            }
                        }
                    )
                browser_result = self._download_with_browser_session(
                    paper,
                    landing_url=landing_url,
                    pdf_urls=pdf_urls,
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                )
                if browser_result is not None:
                    return browser_result
                return last_failure.model_copy(
                    update={
                        "metadata": {
                            **last_failure.metadata,
                            "attempted_pdf_urls": [item.pdf_url for item in failures],
                            "fallback_count": max(len(failures) - 1, 0),
                        }
                    }
                )
            return self._base_result(
                paper,
                status=PaperSourceStatus.RESOLVED_PDF_URL_ONLY,
                source_type=source_type,
                source_url=source_url or pdf_url,
                pdf_url=pdf_url,
                landing_url=landing_url,
                download_status="not_downloaded",
                warnings=[WarningItem(code="PDF_NOT_DOWNLOADED", message="PDF URL is available but was not downloaded.")],
                metadata={"resolution_strategy": "pdf_url_only"},
            )

        if landing_url:
            if self.network_enabled and (download_dir or self.download_dir):
                pmc_result = self._download_pmc_pdf_for_doi(
                    paper,
                    landing_url=landing_url,
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                )
                if pmc_result is not None:
                    return pmc_result
                browser_landing_url = self._publisher_landing_url(landing_url)
                browser_result = self._download_with_browser_session(
                    paper,
                    landing_url=browser_landing_url,
                    pdf_urls=[],
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
                )
                if browser_result is not None:
                    return browser_result
            return self._base_result(
                paper,
                status=PaperSourceStatus.RESOLVED_LANDING_ONLY,
                source_type=PaperSourceType.LANDING_PAGE,
                landing_url=landing_url,
                download_status="not_available",
                warnings=[WarningItem(code="PDF_URL_MISSING", message="No PDF URL is available for this candidate.")],
                metadata={"resolution_strategy": "landing_page_only"},
            )

        return self._base_result(
            paper,
            status=PaperSourceStatus.NO_SOURCE_FOUND,
            source_type=PaperSourceType.METADATA_ONLY,
            download_status="not_available",
            warnings=[
                WarningItem(code="NO_SOURCE_URL", message="No source, landing, DOI, arXiv, or PDF URL found."),
                WarningItem(code="PDF_URL_MISSING", message="No PDF URL is available for this candidate."),
            ],
            error_code="NO_SOURCE_FOUND",
            metadata={"resolution_strategy": "metadata_only"},
        )

    def _publisher_landing_url(self, landing_url: str) -> str:
        """Resolve DOI-only candidates to live-verified browser discovery hosts."""

        parsed = urlparse(landing_url)
        if (parsed.hostname or "").lower() not in {"doi.org", "www.doi.org"}:
            return landing_url
        try:
            with self.http_client.stream(
                "GET",
                landing_url,
                headers={"Range": "bytes=0-0"},
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as response:
                final_url = str(response.url)
        except httpx.HTTPError:
            return landing_url
        final_host = (urlparse(final_url).hostname or "").lower()
        if final_host in BROWSER_DOI_DISCOVERY_HOSTS:
            return final_url
        return landing_url

    def _download_with_browser_session(
        self,
        paper: CandidatePaper,
        *,
        landing_url: str,
        pdf_urls: list[str],
        download_dir: Path,
    ) -> ResolvedPaperSource | None:
        downloader = self.browser_downloader
        if (
            downloader is None
            or not downloader.available
            or not _browser_fallback_eligible(landing_url, pdf_urls)
        ):
            return None
        target = _paper_pdf_path(download_dir, paper)
        result = downloader.download(
            landing_url=landing_url,
            pdf_urls=pdf_urls,
            target_path=target,
            expected_title=paper.title,
        )
        if not result.attempted:
            return None
        if not result.success:
            failure = self._download_failed(
                paper,
                pdf_url=pdf_urls[0] if pdf_urls else "",
                source_url=result.final_url or landing_url,
                landing_url=landing_url,
                source_type=PaperSourceType.PDF if pdf_urls else PaperSourceType.LANDING_PAGE,
                code=result.error_code or "BROWSER_SESSION_FAILED",
                message=result.error or "Authorized browser session did not yield a PDF.",
            )
            return failure.model_copy(
                update={
                    "metadata": {
                        **failure.metadata,
                        **_browser_diagnostic_metadata(
                            result,
                            strategy="authorized_browser_session_failed",
                        ),
                    }
                }
            )
        try:
            content = target.read_bytes()
        except OSError as exc:
            failure = self._download_failed(
                paper,
                pdf_url=result.final_url or (pdf_urls[0] if pdf_urls else ""),
                source_url=result.final_url or landing_url,
                landing_url=landing_url,
                source_type=PaperSourceType.PDF,
                code="BROWSER_SESSION_FILE_MISSING",
                message=str(exc)[:300],
            )
            return failure.model_copy(
                update={
                    "metadata": {
                        **failure.metadata,
                        **_browser_diagnostic_metadata(
                            result,
                            strategy="authorized_browser_session_failed",
                        ),
                    }
                }
            )
        if not content.startswith(PDF_BYTES) or len(content) > self.max_download_bytes:
            target.unlink(missing_ok=True)
            failure = self._download_failed(
                paper,
                pdf_url=result.final_url or (pdf_urls[0] if pdf_urls else ""),
                source_url=result.final_url or landing_url,
                landing_url=landing_url,
                source_type=PaperSourceType.PDF,
                code="BROWSER_SESSION_INVALID_PDF",
                message="Browser-assisted response failed PDF signature or size validation.",
                content_type=result.content_type,
                file_size=len(content),
            )
            return failure.model_copy(
                update={
                    "metadata": {
                        **failure.metadata,
                        **_browser_diagnostic_metadata(
                            result,
                            strategy="authorized_browser_session_failed",
                        ),
                    }
                }
            )
        meta_check, title_match, meta_warning = _check_pdf_metadata(content, paper.title)
        return self._base_result(
            paper,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            source_type=PaperSourceType.PDF,
            source_url=result.final_url or landing_url,
            pdf_url=result.final_url or (pdf_urls[0] if pdf_urls else ""),
            landing_url=landing_url,
            download_status="downloaded",
            final_url=result.final_url,
            content_type=result.content_type or "application/pdf",
            file_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            local_path=str(target),
            pdf_metadata_check=meta_check,
            pdf_title_match=title_match,
            pdf_metadata_warning=meta_warning,
            metadata=_browser_diagnostic_metadata(
                result,
                strategy="authorized_browser_session",
            ),
        )

    def _download_pmc_cloud_pdf(
        self,
        paper: CandidatePaper,
        *,
        pmcid: str,
        landing_url: str,
        download_dir: Path,
    ) -> ResolvedPaperSource | None:
        """Resolve a PMC article through the official versioned AWS dataset.

        PMC article pages can return an HTML preparation screen to server-side
        clients even when the article PDF is openly downloadable.  The current
        PMC Cloud Service exposes versioned metadata and PDF objects without a
        login, so use that machine-access route before scraping the landing page.
        """

        try:
            listing = self.http_client.get(
                f"{PMC_CLOUD_BASE_URL}/",
                params={"list-type": "2", "prefix": f"metadata/{pmcid}."},
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
            listing.raise_for_status()
            if len(listing.content) > 1024 * 1024:
                return None
            root = ET.fromstring(listing.content)
            metadata_keys = [
                str(node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "Key"
                and re.fullmatch(rf"metadata/{re.escape(pmcid)}\.\d+\.json", str(node.text or ""))
            ]
            if not metadata_keys:
                return None
            metadata_key = max(metadata_keys, key=_pmc_metadata_version)
            metadata_url = f"{PMC_CLOUD_BASE_URL}/{metadata_key}"
            metadata_response = self.http_client.get(
                metadata_url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
            metadata_response.raise_for_status()
            if len(metadata_response.content) > 1024 * 1024:
                return None
            metadata = metadata_response.json()
            if str(metadata.get("pmcid") or "").upper() != pmcid:
                return None
            if not (metadata.get("is_pmc_openaccess") or metadata.get("is_manuscript")):
                return None
            pdf_url = _s3_url_to_https(str(metadata.get("pdf_url") or ""))
            if not pdf_url:
                return None
        except (ET.ParseError, ValueError, httpx.HTTPError, OSError):
            return None

        result = self._download_pdf(
            paper,
            pdf_url=pdf_url,
            source_url=metadata_url,
            landing_url=landing_url or f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            source_type=PaperSourceType.PDF,
            download_dir=download_dir,
        )
        if result.status != PaperSourceStatus.RESOLVED_PDF_DOWNLOADED:
            return None
        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "resolution_strategy": "pmc_cloud_pdf",
                    "pmcid": pmcid,
                    "pmc_version": str(metadata.get("version") or _pmc_metadata_version(metadata_key)),
                }
            }
        )

    def _download_pmc_pdf_for_doi(
        self,
        paper: CandidatePaper,
        *,
        landing_url: str,
        download_dir: Path,
    ) -> ResolvedPaperSource | None:
        """Recover an open PMC copy when a publisher route rejected the PDF.

        DOI conversion is intentionally delayed until direct PDF attempts fail,
        avoiding an extra network request for sources that already work.
        """

        doi = _normalize_doi(paper.doi)
        if not doi:
            return None
        try:
            response = self.http_client.get(
                PMC_ID_CONVERTER_URL,
                params={
                    "ids": doi,
                    "idtype": "doi",
                    "format": "json",
                    "tool": "ResearchSensei",
                    "email": "ZehuaGou@users.noreply.github.com",
                },
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            if len(response.content) > 1024 * 1024:
                return None
            payload = response.json()
            records = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                return None
            pmcid = ""
            for record in records:
                if not isinstance(record, dict):
                    continue
                if _normalize_doi(str(record.get("doi") or "")) != doi:
                    continue
                candidate = str(record.get("pmcid") or "").upper()
                if re.fullmatch(r"PMC\d+", candidate):
                    pmcid = candidate
                    break
            if not pmcid:
                return None
        except (ValueError, httpx.HTTPError):
            return None

        return self._download_pmc_cloud_pdf(
            paper,
            pmcid=pmcid,
            landing_url=landing_url,
            download_dir=download_dir,
        )

    def _download_pdf(
        self,
        paper: CandidatePaper,
        *,
        pdf_url: str,
        source_url: str,
        landing_url: str,
        source_type: PaperSourceType,
        download_dir: Path,
    ) -> ResolvedPaperSource:
        import time as _time

        parsed = urlparse(pdf_url)
        if parsed.scheme not in {"http", "https"}:
            return self._download_failed(
                paper,
                pdf_url=pdf_url,
                source_url=source_url,
                landing_url=landing_url,
                source_type=source_type,
                code="INVALID_URL",
                message="PDF URL must use http/https.",
            )

        target = _paper_pdf_path(download_dir, paper)
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = self._existing_pdf_result(
            paper,
            target=target,
            pdf_url=pdf_url,
            source_url=source_url,
            landing_url=landing_url,
            source_type=source_type,
            strategy="existing_named_pdf",
        )
        if existing is not None:
            return existing
        reusable = _find_reusable_pdf(download_dir, target.name, exclude=target)
        if reusable is not None:
            shutil.copy2(reusable, target)
            reused = self._existing_pdf_result(
                paper,
                target=target,
                pdf_url=pdf_url,
                source_url=source_url,
                landing_url=landing_url,
                source_type=source_type,
                strategy="reused_named_pdf",
            )
            if reused is not None:
                return reused

        max_retries = 3
        backoff = [2.0, 4.0, 8.0]
        response = None

        for attempt in range(max_retries):
            try:
                response = self.http_client.get(pdf_url, timeout=self.timeout_seconds, follow_redirects=True)
                if response.status_code in {429, 503} and attempt < max_retries - 1:
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    logger.warning(
                        "PDF download %s got %d, retry %d/%d in %.1fs",
                        pdf_url[:80], response.status_code, attempt + 1, max_retries, wait,
                    )
                    _time.sleep(wait)
                    continue
                response.raise_for_status()
                break
            except (httpx.TimeoutException, httpx.TransportError, OSError) as exc:
                if attempt < max_retries - 1:
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    logger.warning(
                        "PDF download %s error: %s, retry %d/%d in %.1fs",
                        pdf_url[:80], exc, attempt + 1, max_retries, wait,
                    )
                    _time.sleep(wait)
                    continue
                return self._download_failed(
                    paper,
                    pdf_url=pdf_url,
                    source_url=source_url,
                    landing_url=landing_url,
                    source_type=source_type,
                    code="DOWNLOAD_FAILED",
                    message=str(exc)[:300],
                )
            except Exception as exc:
                return self._download_failed(
                    paper,
                    pdf_url=pdf_url,
                    source_url=source_url,
                    landing_url=landing_url,
                    source_type=source_type,
                    code="DOWNLOAD_FAILED",
                    message=str(exc)[:300],
                )

        if response is None:
            return self._download_failed(
                paper,
                pdf_url=pdf_url,
                source_url=source_url,
                landing_url=landing_url,
                source_type=source_type,
                code="DOWNLOAD_FAILED",
                message="No response after retries.",
            )

        content = response.content
        content_length = int(response.headers.get("content-length") or len(content))
        content_type = response.headers.get("content-type", "")
        if content_length > self.max_download_bytes or len(content) > self.max_download_bytes:
            return self._download_failed(
                paper,
                pdf_url=pdf_url,
                source_url=source_url,
                landing_url=landing_url,
                source_type=source_type,
                code="FILE_TOO_LARGE",
                message="Downloaded PDF exceeds configured size limit.",
                content_type=content_type,
                file_size=max(content_length, len(content)),
            )
        if "pdf" not in content_type.lower() and not content.startswith(PDF_BYTES):
            return self._download_failed(
                paper,
                pdf_url=pdf_url,
                source_url=source_url,
                landing_url=landing_url,
                source_type=source_type,
                code="UNSUPPORTED_SOURCE",
                message="Downloaded content is not a PDF.",
                content_type=content_type,
                file_size=len(content),
            )

        target.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()

        # M1.3 lightweight PDF metadata validation
        meta_check, title_match, meta_warning = _check_pdf_metadata(content, paper.title)

        return self._base_result(
            paper,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            source_type=source_type,
            source_url=source_url,
            pdf_url=pdf_url,
            landing_url=landing_url,
            download_status="downloaded",
            final_url=str(response.url),
            content_type=content_type or "application/pdf",
            file_size=target.stat().st_size,
            sha256=sha256,
            local_path=str(target),
            pdf_metadata_check=meta_check,
            pdf_title_match=title_match,
            pdf_metadata_warning=meta_warning,
            metadata={"resolution_strategy": "downloaded_validated_pdf"},
        )

    def _download_failed(
        self,
        paper: CandidatePaper,
        *,
        pdf_url: str,
        source_url: str,
        landing_url: str,
        source_type: PaperSourceType,
        code: str,
        message: str,
        content_type: str = "",
        file_size: int = 0,
    ) -> ResolvedPaperSource:
        return self._base_result(
            paper,
            status=PaperSourceStatus.FAILED_DOWNLOAD,
            source_type=source_type,
            source_url=source_url,
            pdf_url=pdf_url,
            landing_url=landing_url,
            download_status="failed",
            content_type=content_type,
            file_size=file_size,
            warnings=[WarningItem(code=code, message=message)],
            error=message,
            error_code=code,
            metadata={"resolution_strategy": "download_failed"},
        )

    def _download_arxiv_source_result(
        self,
        paper: CandidatePaper,
        *,
        source_url: str,
        pdf_url: str,
        landing_url: str,
        download_dir: Path,
    ) -> ResolvedPaperSource | None:
        if not paper.arxiv_id or not source_url:
            return None
        paper_dir = _paper_source_dir(download_dir, paper)
        paper_dir.mkdir(parents=True, exist_ok=True)
        resolver = SourceResolver(
            http_client=self.http_client,
            timeout_seconds=self.timeout_seconds,
            max_download_bytes=self.max_download_bytes,
        )
        status = resolver._resolve_arxiv_source(
            arxiv_id=paper.arxiv_id,
            source_url=source_url,
            pdf_url=pdf_url,
            run_dir=paper_dir,
        )
        if status is None:
            return None
        source_path = Path(status.resolved_path)
        content = source_path.read_bytes()
        if content.startswith(PDF_BYTES) or status.preferred_m2_input == "pdf":
            meta_check, title_match, meta_warning = _check_pdf_metadata(content, paper.title)
            return self._base_result(
                paper,
                status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
                source_type=PaperSourceType.PDF,
                source_url=source_url,
                pdf_url=pdf_url,
                landing_url=landing_url,
                download_status="downloaded",
                content_type="application/pdf",
                file_size=source_path.stat().st_size,
                sha256=hashlib.sha256(content).hexdigest(),
                local_path=str(source_path),
                warnings=[WarningItem(code=warning, message=warning) for warning in status.warnings],
                pdf_metadata_check=meta_check,
                pdf_title_match=title_match,
                pdf_metadata_warning=meta_warning,
                metadata={
                    "resolution_strategy": status.source_strategy or "arxiv_pdf_fallback",
                    "fallback_used": status.fallback_used,
                },
                source_priority=SourcePriority.PDF,
                preferred_m2_input="pdf",
                has_valid_deep_reading_source=True,
            )
        return self._base_result(
            paper,
            status=PaperSourceStatus.RESOLVED,
            source_type=PaperSourceType.ARXIV_SOURCE,
            source_url=source_url,
            pdf_url=pdf_url,
            landing_url=landing_url,
            download_status="downloaded",
            content_type=status.content_type or "text/x-tex",
            file_size=source_path.stat().st_size,
            sha256=hashlib.sha256(content).hexdigest(),
            local_path=str(source_path),
            warnings=[WarningItem(code=warning, message=warning) for warning in status.warnings],
            metadata={
                "resolution_strategy": "downloaded_arxiv_source",
                "source_manifest_path": status.source_manifest_path,
                "source_dir": status.source_dir,
            },
            source_priority=SourcePriority.LATEX_SOURCE,
            preferred_m2_input="latex_source",
            has_valid_deep_reading_source=True,
            latex_source_available=True,
            latex_source_downloaded=True,
            latex_main_file=status.latex_main_file,
            latex_source_path=status.latex_source_path,
        )

    def _existing_pdf_result(
        self,
        paper: CandidatePaper,
        *,
        target: Path,
        pdf_url: str,
        source_url: str,
        landing_url: str,
        source_type: PaperSourceType,
        strategy: str,
    ) -> ResolvedPaperSource | None:
        if not target.exists() or not target.is_file():
            return None
        try:
            content = target.read_bytes()
        except OSError:
            return None
        if not content.startswith(PDF_BYTES):
            return None
        sha256 = hashlib.sha256(content).hexdigest()
        meta_check, title_match, meta_warning = _check_pdf_metadata(content, paper.title)
        return self._base_result(
            paper,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            source_type=source_type,
            source_url=source_url,
            pdf_url=pdf_url,
            landing_url=landing_url,
            download_status="downloaded",
            content_type="application/pdf",
            file_size=target.stat().st_size,
            sha256=sha256,
            local_path=str(target),
            pdf_metadata_check=meta_check,
            pdf_title_match=title_match,
            pdf_metadata_warning=meta_warning,
            metadata={"resolution_strategy": strategy},
        )

    def _library_reuse_result(
        self,
        paper: CandidatePaper,
        record: PaperLibraryRecord,
    ) -> ResolvedPaperSource:
        path = Path(record.local_path)
        content = path.read_bytes()
        sha256 = record.sha256 or hashlib.sha256(content).hexdigest()
        is_pdf = content.startswith(PDF_BYTES)
        meta_check = "skipped"
        title_match = "unknown"
        meta_warning = ""
        if is_pdf:
            meta_check, title_match, meta_warning = _check_pdf_metadata(content, paper.title)
        source_type = PaperSourceType.PDF if is_pdf else PaperSourceType.ARXIV_SOURCE
        source_priority = SourcePriority.PDF if is_pdf else SourcePriority.LATEX_SOURCE
        preferred_m2_input = "pdf" if is_pdf else "latex_source"
        return self._base_result(
            paper,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED if is_pdf else PaperSourceStatus.RESOLVED,
            source_type=source_type,
            source_url=paper.source_url or record.pdf_url or record.landing_url,
            pdf_url=paper.pdf_url or record.pdf_url,
            landing_url=paper.landing_url or record.landing_url,
            download_status="downloaded",
            content_type="application/pdf" if is_pdf else "application/octet-stream",
            file_size=record.file_size or path.stat().st_size,
            sha256=sha256,
            local_path=str(path),
            pdf_metadata_check=meta_check,
            pdf_title_match=title_match,
            pdf_metadata_warning=meta_warning,
            metadata={
                "resolution_strategy": "library_reuse",
                "library_paper_id": record.paper_id,
            },
            source_priority=source_priority,
            preferred_m2_input=preferred_m2_input,
            has_valid_deep_reading_source=True,
        )

    @staticmethod
    def _write_search_manifest(
        download_dir: Path,
        query: str,
        candidates: list[CandidatePaper],
        items: list[ResolvedPaperSource],
    ) -> None:
        download_dir.mkdir(parents=True, exist_ok=True)
        by_id = {item.paper_id: item for item in items}
        papers: list[dict[str, object]] = []
        for candidate in candidates:
            item = by_id.get(candidate.paper_id)
            papers.append({
                "paper_id": candidate.paper_id,
                "title": candidate.title,
                "authors": candidate.authors,
                "year": candidate.year,
                "venue": candidate.venue,
                "venue_canonical_name": candidate.venue_canonical_name,
                "venue_rank": candidate.venue_rank.value,
                "download_selected": candidate.download_selected,
                "download_decision": candidate.download_decision,
                "download_reason": candidate.download_reason,
                "search_rank": candidate.search_rank,
                "rerank_rank": candidate.rerank_rank,
                "rerank_score": candidate.rerank_score,
                "rank_score": candidate.rank_score,
                "rank_reason": candidate.rank_reason,
                "selected_fulltext_source": candidate.selected_fulltext_source,
                "pdf_url": candidate.pdf_url,
                "landing_url": candidate.landing_url or candidate.url,
                "local_path": item.local_path if item is not None else "",
                "download_status": item.download_status if item is not None else "not_attempted",
                "source_status": item.status.value if item is not None else "",
                "source_type": item.source_type.value if item is not None else "",
                "sha256": item.sha256 if item is not None else "",
                "error_code": item.error_code if item is not None else "",
                "resolution_strategy": item.metadata.get("resolution_strategy", "") if item is not None else "",
                "browser_mode": item.metadata.get("browser_mode", "") if item is not None else "",
                "cookie_consent_detected": item.metadata.get("cookie_consent_detected", "") if item is not None else "",
                "cookie_consent_action": item.metadata.get("cookie_consent_action", "") if item is not None else "",
                "cookie_consent_dismissed": item.metadata.get("cookie_consent_dismissed", "") if item is not None else "",
                "consent_screenshot": item.metadata.get("consent_screenshot", "") if item is not None else "",
                "diagnostic_screenshot": item.metadata.get("diagnostic_screenshot", "") if item is not None else "",
                "page_barrier": item.metadata.get("page_barrier", "") if item is not None else "",
            })
        manifest = {
            "query": query,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "download_dir": str(download_dir),
            "paper_count": len(papers),
            "downloaded_count": sum(1 for paper in papers if paper.get("download_status") == "downloaded"),
            "papers": papers,
        }
        (download_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        readme_lines = [
            f"# {query}",
            "",
            f"- downloaded_count: {manifest['downloaded_count']}",
            f"- paper_count: {manifest['paper_count']}",
            "",
            "| Paper | Venue | CCF | File |",
            "|---|---|---:|---|",
        ]
        for paper in papers:
            local_path = str(paper.get("local_path") or "")
            filename = Path(local_path).name if local_path else ""
            readme_lines.append(
                f"| {paper.get('title') or ''} | {paper.get('venue_canonical_name') or paper.get('venue') or ''} | "
                f"{paper.get('venue_rank') or ''} | {filename} |"
            )
        (download_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    def _base_result(
        self,
        paper: CandidatePaper,
        *,
        status: PaperSourceStatus,
        source_type: PaperSourceType,
        source_url: str = "",
        pdf_url: str = "",
        landing_url: str = "",
        download_status: str = "",
        final_url: str = "",
        content_type: str = "",
        file_size: int = 0,
        sha256: str = "",
        local_path: str = "",
        warnings: list[WarningItem] | None = None,
        error: str = "",
        error_code: str = "",
        metadata: dict[str, str] | None = None,
        pdf_metadata_check: str = "",
        pdf_title_match: str = "",
        pdf_metadata_warning: str = "",
        source_priority: SourcePriority | None = None,
        preferred_m2_input: str = "",
        has_valid_deep_reading_source: bool | None = None,
        latex_source_available: bool = False,
        latex_source_downloaded: bool = False,
        latex_main_file: str = "",
        latex_source_path: str = "",
    ) -> ResolvedPaperSource:
        has_valid_pdf = bool(
            status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
            and local_path
            and sha256
            and file_size > 0
        )
        actual_source_priority = source_priority or (SourcePriority.PDF if has_valid_pdf else SourcePriority.METADATA_ONLY)
        actual_preferred_m2_input = preferred_m2_input or ("pdf" if has_valid_pdf else "none")
        actual_valid_source = has_valid_deep_reading_source if has_valid_deep_reading_source is not None else has_valid_pdf
        return ResolvedPaperSource(
            paper_id=paper.paper_id,
            title=paper.title,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            source_url=source_url,
            pdf_url=pdf_url,
            landing_url=landing_url,
            source_type=source_type,
            status=status,
            download_status=download_status,
            final_url=final_url,
            content_type=content_type,
            file_size=file_size,
            sha256=sha256,
            local_path=local_path,
            error_code=error_code,
            warnings=warnings or [],
            error=error,
            metadata=metadata or {},
            pdf_metadata_check=pdf_metadata_check,
            pdf_title_match=pdf_title_match,
            pdf_metadata_warning=pdf_metadata_warning,
            source_priority=actual_source_priority,
            preferred_m2_input=actual_preferred_m2_input,
            has_valid_deep_reading_source=actual_valid_source,
            latex_source_available=latex_source_available,
            latex_source_downloaded=latex_source_downloaded,
            latex_main_file=latex_main_file,
            latex_source_path=latex_source_path,
        )

    @staticmethod
    def arxiv_to_source_url(arxiv_id: str) -> str:
        clean = arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
        return f"https://arxiv.org/e-print/{clean}" if _is_valid_arxiv_id(clean) else ""

    @staticmethod
    def arxiv_to_abs_url(arxiv_id: str) -> str:
        clean = arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
        return f"https://arxiv.org/abs/{clean}" if _is_valid_arxiv_id(clean) else ""


class SourceResolver:
    """Phase 5 source resolver for upload/local/pdf-url/arXiv input parsing."""

    def __init__(
        self,
        *,
        allowed_roots: list[str | Path] | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_download_bytes: int = 80 * 1024 * 1024,
    ) -> None:
        self.allowed_roots = [Path(root).resolve() for root in allowed_roots or []]
        self.http_client = http_client or httpx.Client()
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self._last_arxiv_source_fallback = ""

    def resolve_upload(self, source_path: str | Path, *, original_filename: str, content_type: str = "") -> SourceStatus:
        path = Path(source_path)
        return SourceStatus(
            source_type="upload",
            original_input=original_filename,
            resolved_path=str(path),
            status="resolved",
            content_type=content_type,
            size_bytes=path.stat().st_size if path.exists() else 0,
        )

    def resolve_local_path(self, local_path: str | Path, *, run_dir: str | Path) -> SourceStatus:
        original = str(local_path)
        source = Path(local_path)
        try:
            resolved_source = source.resolve(strict=True)
        except OSError:
            return _status(
                source_type="local_path",
                original_input=original,
                status="failed",
                warnings=["FULL_TEXT_MISSING"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )

        if not self._is_allowed(resolved_source):
            return _status(
                source_type="local_path",
                original_input=original,
                status="rejected",
                warnings=["SECURITY_REJECTED"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )

        suffix = resolved_source.suffix.lower()
        if suffix not in SUPPORTED_LOCAL_SUFFIXES:
            return _status(
                source_type="local_path",
                original_input=original,
                status="rejected",
                warnings=["UNSUPPORTED_SOURCE"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )

        target = Path(run_dir) / f"source{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, target)
        return SourceStatus(
            source_type="local_path",
            original_input=original,
            resolved_path=str(target),
            status="resolved",
            content_type=_content_type_for_suffix(suffix),
            size_bytes=target.stat().st_size,
            source_strategy="local_path",
            source_priority="latex_source" if suffix == ".tex" else ("pdf" if suffix == ".pdf" else "low_confidence_text"),
            preferred_m2_input="latex_source" if suffix == ".tex" else ("pdf" if suffix == ".pdf" else "text"),
            latex_source_available=suffix == ".tex",
            latex_source_path=str(target) if suffix == ".tex" else "",
            latex_main_file=str(target) if suffix == ".tex" else "",
        )

    def resolve_pdf_url(self, pdf_url: str, run_dir: str | Path) -> SourceStatus:
        parsed = urlparse(pdf_url)
        if parsed.scheme not in {"http", "https"}:
            return _status(
                source_type="pdf_url",
                original_input=pdf_url,
                status="rejected",
                warnings=["UNSUPPORTED_SOURCE", "INVALID_URL"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )

        try:
            response = self.http_client.get(pdf_url, timeout=self.timeout_seconds, follow_redirects=True)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("PDF download failed for %s: %s", pdf_url, exc)
            return _status(
                source_type="pdf_url",
                original_input=pdf_url,
                status="failed",
                warnings=["DOWNLOAD_FAILED", str(exc)[:200]],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )

        content = response.content
        content_length = int(response.headers.get("content-length") or len(content))
        if content_length > self.max_download_bytes or len(content) > self.max_download_bytes:
            return _status(
                source_type="pdf_url",
                original_input=pdf_url,
                status="rejected",
                warnings=["FILE_TOO_LARGE", "DOWNLOAD_TOO_LARGE"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
                size_bytes=max(content_length, len(content)),
                content_type=response.headers.get("content-type", ""),
            )

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not content.startswith(PDF_BYTES):
            return _status(
                source_type="pdf_url",
                original_input=pdf_url,
                status="rejected",
                warnings=["UNSUPPORTED_SOURCE"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
                size_bytes=len(content),
                content_type=content_type,
            )

        target = Path(run_dir) / "source.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return SourceStatus(
            source_type="pdf_url",
            original_input=pdf_url,
            resolved_path=str(target),
            status="resolved",
            content_type=content_type or "application/pdf",
            size_bytes=target.stat().st_size,
            pdf_url=pdf_url,
            source_strategy="pdf_direct",
            source_priority="pdf",
            preferred_m2_input="pdf",
        )

    def resolve_arxiv_id(self, arxiv_id: str, run_dir: str | Path) -> SourceStatus:
        pdf_url = self.arxiv_to_pdf_url(arxiv_id=arxiv_id)
        source_url = self.arxiv_to_source_url(arxiv_id=arxiv_id)
        if not pdf_url:
            return _status(
                source_type="arxiv_id",
                original_input=arxiv_id,
                status="rejected",
                warnings=["INVALID_ARXIV_ID"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )
        source_status = self._resolve_arxiv_source(arxiv_id=arxiv_id, source_url=source_url, pdf_url=pdf_url, run_dir=run_dir)
        if source_status is not None:
            return source_status
        status = self.resolve_pdf_url(pdf_url, run_dir)
        fallback = self._last_arxiv_source_fallback or status.fallback_used or "source_unavailable"
        return status.model_copy(
            update={
                "source_type": "arxiv_pdf",
                "original_input": arxiv_id,
                "source_url": source_url,
                "pdf_url": pdf_url,
                "source_strategy": "pdf_fallback" if status.status == "resolved" else "source_first_failed",
                "fallback_used": fallback,
                "warnings": _unique_warnings(["ARXIV_SOURCE_UNAVAILABLE", fallback, *status.warnings]),
            }
        )

    def resolve_arxiv_url(self, arxiv_url: str, run_dir: str | Path) -> SourceStatus:
        pdf_url = self.arxiv_to_pdf_url(arxiv_url=arxiv_url)
        arxiv_id = self.arxiv_id_from_url(arxiv_url)
        source_url = self.arxiv_to_source_url(arxiv_id=arxiv_id) if arxiv_id else ""
        if not pdf_url:
            return _status(
                source_type="arxiv_url",
                original_input=arxiv_url,
                status="rejected",
                warnings=["INVALID_ARXIV_ID"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )
        if arxiv_id:
            source_status = self._resolve_arxiv_source(arxiv_id=arxiv_id, source_url=source_url, pdf_url=pdf_url, run_dir=run_dir)
            if source_status is not None:
                return source_status.model_copy(update={"original_input": arxiv_url})
        status = self.resolve_pdf_url(pdf_url, run_dir)
        fallback = self._last_arxiv_source_fallback or status.fallback_used or "source_unavailable"
        return status.model_copy(
            update={
                "source_type": "arxiv_pdf",
                "original_input": arxiv_url,
                "source_url": source_url,
                "pdf_url": pdf_url,
                "source_strategy": "pdf_fallback" if status.status == "resolved" else "source_first_failed",
                "fallback_used": fallback,
                "warnings": _unique_warnings(["ARXIV_SOURCE_UNAVAILABLE", fallback, *status.warnings]),
            }
        )

    def _resolve_arxiv_source(
        self,
        *,
        arxiv_id: str,
        source_url: str,
        pdf_url: str,
        run_dir: str | Path,
    ) -> SourceStatus | None:
        if not source_url:
            self._last_arxiv_source_fallback = "source_unavailable"
            return None
        self._last_arxiv_source_fallback = ""
        response = None
        last_error: Exception | None = None
        clean_id = _clean_arxiv_id(arxiv_id)
        candidate_urls = list(dict.fromkeys(filter(None, [
            source_url,
            f"https://arxiv.org/src/{clean_id}" if _is_valid_arxiv_id(clean_id) else "",
        ])))
        retry_delays = (1.0, 2.0)
        for candidate_url in candidate_urls:
            for attempt in range(len(retry_delays) + 1):
                try:
                    candidate_response = self.http_client.get(
                        candidate_url,
                        timeout=self.timeout_seconds,
                        follow_redirects=True,
                    )
                    if (
                        getattr(candidate_response, "status_code", 200) in {429, 502, 503, 504}
                        and attempt < len(retry_delays)
                    ):
                        import time

                        delay = retry_delays[attempt]
                        logger.warning(
                            "arXiv source %s got %s, retry %d/%d in %.1fs",
                            candidate_url,
                            candidate_response.status_code,
                            attempt + 1,
                            len(retry_delays) + 1,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    candidate_response.raise_for_status()
                    content_type = candidate_response.headers.get("content-type", "")
                    if candidate_response.content and not (
                        candidate_response.content.startswith(PDF_BYTES)
                        or "pdf" in content_type.lower()
                    ):
                        response = candidate_response
                        break
                    last_error = ValueError("arXiv source endpoint returned PDF or empty content")
                    break
                except (httpx.TimeoutException, httpx.TransportError, OSError) as exc:
                    last_error = exc
                    if attempt < len(retry_delays):
                        import time

                        delay = retry_delays[attempt]
                        logger.warning(
                            "arXiv source %s transport error: %s; retry %d/%d in %.1fs",
                            candidate_url,
                            exc,
                            attempt + 1,
                            len(retry_delays) + 1,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    break
                except Exception as exc:
                    last_error = exc
                    break
            if response is not None:
                break

        if response is None:
            logger.info("arXiv source download failed for %s, falling back to PDF: %s", arxiv_id, last_error)
            self._last_arxiv_source_fallback = "source_unavailable"
            return None

        content = response.content
        content_length = int(response.headers.get("content-length") or len(content))
        content_type = response.headers.get("content-type", "")
        if content_length > self.max_download_bytes or len(content) > self.max_download_bytes:
            logger.warning("arXiv source %s exceeds configured size limit; falling back to PDF.", arxiv_id)
            self._last_arxiv_source_fallback = "source_unavailable"
            return None
        source_dir = Path(run_dir) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        raw_name = "source.tar.gz" if (content.startswith(GZIP_BYTES) or "gzip" in content_type.lower()) else "source.tex"
        raw_path = source_dir / raw_name
        raw_path.write_bytes(content)

        materialize_result = materialize_latex_source(content, source_dir=source_dir)
        main_tex = materialize_result.main_tex
        manifest_path = source_dir / "source_manifest.json"
        manifest = {
            "arxiv_id": arxiv_id,
            "source_url": source_url,
            "download_url": str(response.url),
            "pdf_url": pdf_url,
            "raw_path": str(raw_path),
            "source_dir": str(source_dir),
            "main_tex": str(main_tex) if main_tex else "",
            "main_tex_selection_reason": materialize_result.selection_reason,
            "extracted_files": [str(path) for path in materialize_result.extracted_files],
            "warnings": materialize_result.warnings,
            "strategy": "source_first",
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if main_tex is None:
            logger.info("arXiv source for %s did not expose a usable .tex file; falling back to PDF.", arxiv_id)
            self._last_arxiv_source_fallback = "source_parse_failed"
            return None

        return SourceStatus(
            source_type="arxiv_source",
            original_input=arxiv_id,
            resolved_path=str(main_tex),
            status="resolved",
            warnings=materialize_result.warnings,
            content_type="text/x-tex",
            size_bytes=main_tex.stat().st_size,
            source_url=source_url,
            pdf_url=pdf_url,
            source_dir=str(source_dir),
            source_manifest_path=str(manifest_path),
            source_strategy="source_first",
            source_priority="latex_source",
            preferred_m2_input="latex_source",
            latex_source_available=True,
            latex_source_path=str(main_tex),
            latex_main_file=str(main_tex),
        )

    @staticmethod
    def arxiv_to_pdf_url(*, arxiv_id: str = "", arxiv_url: str = "") -> str:
        if arxiv_id:
            clean = arxiv_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
            return f"https://arxiv.org/pdf/{clean}.pdf" if _is_valid_arxiv_id(clean) else ""

        parsed = urlparse(arxiv_url)
        if parsed.netloc.lower() != "arxiv.org":
            return ""
        path = parsed.path.strip("/")
        if path.startswith("abs/"):
            clean = path.removeprefix("abs/")
            return f"https://arxiv.org/pdf/{clean}.pdf" if _is_valid_arxiv_id(clean) else ""
        if path.startswith("pdf/"):
            clean = path.removeprefix("pdf/").removesuffix(".pdf")
            return f"https://arxiv.org/pdf/{clean}.pdf" if _is_valid_arxiv_id(clean) else ""
        if path.startswith("e-print/"):
            clean = path.removeprefix("e-print/")
            return f"https://arxiv.org/pdf/{clean}.pdf" if _is_valid_arxiv_id(clean) else ""
        return ""

    @staticmethod
    def arxiv_to_source_url(*, arxiv_id: str = "", arxiv_url: str = "") -> str:
        clean = _clean_arxiv_id(arxiv_id) if arxiv_id else SourceResolver.arxiv_id_from_url(arxiv_url)
        return f"https://arxiv.org/e-print/{clean}" if _is_valid_arxiv_id(clean) else ""

    @staticmethod
    def arxiv_id_from_url(arxiv_url: str) -> str:
        parsed = urlparse(arxiv_url)
        if parsed.netloc.lower() != "arxiv.org":
            return ""
        path = parsed.path.strip("/")
        if path.startswith("abs/"):
            clean = path.removeprefix("abs/")
            return clean if _is_valid_arxiv_id(clean) else ""
        if path.startswith("pdf/"):
            clean = path.removeprefix("pdf/").removesuffix(".pdf")
            return clean if _is_valid_arxiv_id(clean) else ""
        if path.startswith("e-print/"):
            clean = path.removeprefix("e-print/")
            return clean if _is_valid_arxiv_id(clean) else ""
        return ""

    def _is_allowed(self, path: Path) -> bool:
        if not self.allowed_roots:
            return True
        for root in self.allowed_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False


def _status(
    *,
    source_type: str,
    original_input: str,
    status: str,
    warnings: list[str],
    degraded_flags: list[str],
    resolved_path: str = "",
    content_type: str = "",
    size_bytes: int = 0,
    source_url: str = "",
    pdf_url: str = "",
    source_strategy: str = "",
    source_priority: str = "",
    preferred_m2_input: str = "",
    fallback_used: str = "",
) -> SourceStatus:
    return SourceStatus(
        source_type=source_type,
        original_input=original_input,
        resolved_path=resolved_path,
        status=status,
        warnings=warnings,
        degraded_flags=degraded_flags,
        content_type=content_type,
        size_bytes=size_bytes,
        source_url=source_url,
        pdf_url=pdf_url,
        source_strategy=source_strategy,
        source_priority=source_priority,
        preferred_m2_input=preferred_m2_input,
        fallback_used=fallback_used,
    )


def _is_valid_arxiv_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", value))


def _clean_arxiv_id(value: str) -> str:
    return value.strip().removeprefix("arXiv:").removeprefix("arxiv:")


def _doi_url(doi: str) -> str:
    clean = _normalize_doi(doi)
    if not clean:
        return ""
    return f"https://doi.org/{clean}"


def _normalize_doi(doi: str) -> str:
    clean = str(doi or "").strip()
    lower = clean.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lower.startswith(prefix):
            clean = clean[len(prefix) :].strip()
            break
    return clean.lower()


def _content_type_for_suffix(suffix: str) -> str:
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".tex": "text/x-tex",
    }.get(suffix, "")


def materialize_latex_source(content: bytes, *, source_dir: Path) -> LatexSourceMaterialization:
    """Write/extract arXiv e-print content and locate the safest main tex file."""

    extracted_dir = source_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    extracted_files: list[Path] = []

    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = member.name.replace("\\", "/").lstrip("/")
                if ".." in Path(member_name).parts:
                    warnings.append(f"SKIPPED_UNSAFE_SOURCE_MEMBER:{member.name}")
                    continue
                target = (extracted_dir / member_name).resolve()
                try:
                    target.relative_to(extracted_dir.resolve())
                except ValueError:
                    warnings.append(f"SKIPPED_UNSAFE_SOURCE_MEMBER:{member.name}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                fileobj = archive.extractfile(member)
                if fileobj is None:
                    continue
                data = fileobj.read()
                target.write_bytes(data)
                extracted_files.append(target)
    except tarfile.TarError:
        extracted_files.extend(_write_non_tar_latex_source(content, extracted_dir, warnings))

    main_tex, reason = select_latex_main_file(extracted_dir)
    if main_tex is None:
        warnings.append("LATEX_MAIN_NOT_FOUND")
    return LatexSourceMaterialization(
        main_tex=main_tex,
        selection_reason=reason,
        extracted_files=extracted_files,
        warnings=warnings,
    )


def _write_non_tar_latex_source(content: bytes, extracted_dir: Path, warnings: list[str]) -> list[Path]:
    data = content
    if content.startswith(GZIP_BYTES):
        try:
            data = gzip.decompress(content)
        except OSError:
            warnings.append("SOURCE_GZIP_DECOMPRESS_FAILED")
            data = content
    target = extracted_dir / "source.tex"
    target.write_bytes(data)
    return [target]


def select_latex_main_file(source_dir: str | Path) -> tuple[Path | None, str]:
    root = Path(source_dir)
    tex_files = [path for path in root.rglob("*.tex") if path.is_file()]
    if not tex_files:
        return None, "no_tex_files"

    documentclass_matches: list[tuple[float, Path]] = []
    for path in tex_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        active_text = re.sub(r"(?m)(?<!\\)%.*$", "", text)
        if re.search(r"(?m)^\s*\\documentclass(?:\[[^\]]*\])?\{", active_text):
            relative = path.relative_to(root)
            path_words = {part.lower() for part in relative.parts}
            stem_words = set(re.split(r"[^a-z0-9]+", path.stem.lower()))
            template_markers = {"sample", "template", "example", "demo", "test"}
            template_penalty = 1_000 if path_words & template_markers or stem_words & template_markers else 0
            include_count = len(re.findall(r"\\(?:input|include)\s*\{", active_text))
            score = (
                200
                + (80 if "\\begin{document}" in active_text else 0)
                + (60 if re.search(r"\\title\s*\{", active_text) else 0)
                + min(include_count * 12, 120)
                + min(path.stat().st_size / 1024, 50)
                - max(len(relative.parts) - 1, 0) * 20
                - template_penalty
            )
            documentclass_matches.append((score, path))
    if documentclass_matches:
        documentclass_matches.sort(key=lambda item: (item[0], str(item[1]).lower()), reverse=True)
        return documentclass_matches[0][1], "documentclass"

    tex_files.sort(key=lambda path: path.stat().st_size, reverse=True)
    return tex_files[0], "largest_tex"


def _ordered_pdf_urls(values: list[str]) -> list[str]:
    """Prefer stable OA/repository endpoints while retaining publisher fallbacks."""

    unique: list[str] = []
    for value in values:
        url = str(value or "").strip()
        lower = url.lower()
        if not url.startswith(("http://", "https://")):
            continue
        if not (
            lower.endswith(".pdf")
            or "/pdf" in lower
            or "pdf" in lower
            or "ojs.aaai.org" in lower and "/article/download/" in lower
        ):
            continue
        if url not in unique:
            unique.append(url)

    def reliability(url: str) -> int:
        lower = url.lower()
        if any(
            marker in lower
            for marker in (
                "arxiv.org/",
                "pmc.ncbi.nlm.nih.gov/",
                "pdfs.semanticscholar.org/",
                "ojs.aaai.org/",
                "aaai.org/ojs/",
                "ijcai.org/proceedings/",
                "proceedings.mlr.press/",
                "openaccess.thecvf.com/",
                "aclanthology.org/",
                "eprints.",
                "repository.",
                "hal.science/",
            )
        ):
            return 0
        if "mdpi.com/" in lower:
            return 2
        if any(marker in lower for marker in ("dl.acm.org/", "ieeexplore.ieee.org/", "sciencedirect.com/")):
            return 3
        return 1

    return sorted(unique, key=reliability)


def _paper_pmcid(paper: CandidatePaper) -> str:
    values = [
        paper.url,
        paper.landing_url,
        paper.pdf_url,
        paper.selected_fulltext_url,
        *paper.candidate_pdf_urls,
        *paper.candidate_html_urls,
        json.dumps(paper.raw_source_metadata, ensure_ascii=True, default=str),
    ]
    for value in values:
        match = re.search(r"\bPMC\d+\b", str(value or ""), flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return ""


def _browser_fallback_eligible(landing_url: str, pdf_urls: list[str]) -> bool:
    """Use native Chrome only when it can plausibly expose full text.

    A concrete PDF candidate is always worth retrying with the authorized
    session. A publisher landing page may expose a JavaScript download button.
    Metadata/index pages cannot create a PDF after all OA resolution stages
    already failed, so opening Chrome for them only adds latency and windows.
    """

    if any(url.startswith(("http://", "https://")) for url in pdf_urls):
        return True
    host = urlparse(landing_url).hostname or ""
    return bool(host and host.lower() not in BROWSER_METADATA_HOSTS)


def _browser_diagnostic_metadata(
    result: BrowserDownloadResult,
    *,
    strategy: str,
) -> dict[str, str]:
    metadata: dict[str, str] = {
        "resolution_strategy": strategy,
        "browser_mode": result.browser_mode or "native_chrome_cdp",
    }
    if result.cookie_consent_detected:
        metadata["cookie_consent_detected"] = "true"
        metadata["cookie_consent_dismissed"] = str(result.cookie_consent_dismissed).lower()
    if result.cookie_consent_action:
        metadata["cookie_consent_action"] = result.cookie_consent_action
    if result.consent_screenshot:
        metadata["consent_screenshot"] = result.consent_screenshot
    if result.diagnostic_screenshot:
        metadata["diagnostic_screenshot"] = result.diagnostic_screenshot
    if result.page_barrier:
        metadata["page_barrier"] = result.page_barrier
    return metadata


def _pmc_metadata_version(key: str) -> int:
    match = re.search(r"\.(\d+)\.json$", key)
    return int(match.group(1)) if match else 0


def _s3_url_to_https(value: str) -> str:
    match = re.fullmatch(r"s3://([^/]+)/(.+)", value.strip())
    if not match:
        return value if value.startswith(("http://", "https://")) else ""
    bucket, key = match.groups()
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def _unique_warnings(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "paper"


def _paper_pdf_path(download_dir: Path, paper: CandidatePaper) -> Path:
    return download_dir / f"{_safe_file_stem(paper.title or paper.paper_id)}.pdf"


def _paper_source_dir(download_dir: Path, paper: CandidatePaper) -> Path:
    return download_dir / f"{_safe_file_stem(paper.title or paper.paper_id)}__source"


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"^(?:\[[A-Z]+\]\s*)+", "", value or "").strip()
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", safe).strip()
    safe = re.sub(r"\s+", " ", safe)
    safe = safe.rstrip(" .")
    return safe[:140] or _safe_name(value)


def _find_reusable_pdf(download_dir: Path, filename: str, *, exclude: Path) -> Path | None:
    root = download_dir.parent
    if not root.exists():
        return None
    try:
        exclude_resolved = exclude.resolve()
    except OSError:
        exclude_resolved = exclude
    for candidate in root.glob(f"*/{filename}"):
        try:
            if candidate.resolve() == exclude_resolved:
                continue
            if candidate.is_file() and candidate.read_bytes().startswith(PDF_BYTES):
                return candidate
        except OSError:
            continue
    return None


def _check_pdf_metadata(content: bytes, expected_title: str) -> tuple[str, str, str]:
    """M1.3 PDF metadata/title validation.

    Returns (pdf_metadata_check, pdf_title_match, pdf_metadata_warning).
    1. Check %PDF header.
    2. Try fitz (PyMuPDF) to read metadata and first-page text.
    3. Check title token overlap between expected title and PDF content.
    """
    if not expected_title:
        return ("skipped", "unknown", "No expected title to compare against.")

    if not content.startswith(PDF_BYTES):
        return ("failed", "unknown", "Content does not start with %PDF header.")

    # Try fitz for metadata + first-page text
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=content, filetype="pdf") as doc:
            # Metadata title
            meta_title = (doc.metadata or {}).get("title", "").strip()

            # First-page text (first 2000 chars)
            first_page_text = ""
            if len(doc) > 0:
                first_page_text = doc[0].get_text()[:2000]

            # Check title tokens against metadata title and first-page text
            expected_tokens = _title_tokens(expected_title)
            if not expected_tokens:
                return ("passed", "unknown", "Expected title has no meaningful tokens.")

            # Try metadata title first
            if meta_title:
                if _titles_match_for_pdf(expected_title, meta_title):
                    return ("passed", "match", "")
                # Metadata title exists but doesn't match — check first page as backup
                meta_match = _title_token_overlap(expected_tokens, _title_tokens(meta_title))
                page_match = _title_token_overlap(expected_tokens, _title_tokens(first_page_text))
                if page_match >= 0.6:
                    return ("passed", "match", f"PDF metadata title mismatch but first-page tokens match ({page_match:.0%}).")
                return ("passed", "mismatch", f"PDF metadata title '{meta_title[:80]}' does not match expected title. Token overlap: {meta_match:.0%}.")

            # No metadata title — check first page text
            if first_page_text.strip():
                page_match = _title_token_overlap(expected_tokens, _title_tokens(first_page_text))
                if page_match >= 0.6:
                    return ("passed", "match", f"Title matched via first-page text tokens ({page_match:.0%}).")
                if page_match >= 0.3:
                    return ("passed", "unknown", f"Partial title token overlap in first page ({page_match:.0%}). Cannot confirm.")
                return ("passed", "unknown", f"Low title token overlap in first page ({page_match:.0%}). PDF may not contain expected paper.")

            # No text at all (scanned/image PDF)
            return ("text_unavailable", "unknown", "No extractable text on first page (may be scanned PDF).")

    except ImportError:
        # fitz not available — fall back to header scan
        pass
    except Exception as exc:
        return ("passed", "unknown", f"fitz PDF parsing error: {type(exc).__name__}: {str(exc)[:100]}")

    # Fallback: scan first 64KB for /Title in PDF header
    header_chunk = content[: 64 * 1024]
    try:
        header_text = header_chunk.decode("latin-1", errors="ignore")
    except Exception:
        return ("passed", "unknown", "Could not decode PDF header for metadata check.")

    meta_title = _extract_pdf_title_from_header(header_text)
    if meta_title is None:
        return ("passed", "unknown", "No /Title metadata found in PDF header.")

    match_result = "match" if _titles_match_for_pdf(expected_title, meta_title) else "mismatch"
    warning = "" if match_result == "match" else f"PDF /Title '{meta_title[:80]}' does not match expected title."
    return ("passed", match_result, warning)


def _title_tokens(title: str) -> list[str]:
    """Extract meaningful tokens from a title (>2 chars, lowercase)."""
    import re as _re
    return [t for t in _re.sub(r"[^a-z0-9]+", " ", title.lower()).split() if len(t) > 2]


def _title_token_overlap(expected_tokens: list[str], actual_tokens: list[str]) -> float:
    """Compute Jaccard-like overlap: fraction of expected tokens found in actual."""
    if not expected_tokens:
        return 0.0
    actual_set = set(actual_tokens)
    hits = sum(1 for t in expected_tokens if t in actual_set)
    return hits / len(expected_tokens)


def _extract_pdf_title_from_header(header_text: str) -> str | None:
    """Extract /Title from PDF metadata header section."""
    import re as _re
    match = _re.search(r"/Title\s*\(([^)]{1,200})\)", header_text)
    if match:
        return match.group(1).strip()
    match = _re.search(r"/Title\s*<([0-9A-Fa-f\s]{2,400})>", header_text)
    if match:
        hex_str = match.group(1).replace(" ", "")
        try:
            return bytes.fromhex(hex_str).decode("utf-16-be", errors="ignore").strip()
        except Exception:
            pass
    return None


def _titles_match_for_pdf(expected: str, pdf_title: str) -> bool:
    """Fuzzy title match for PDF metadata validation."""
    import re as _re
    norm_expected = _re.sub(r"[^a-z0-9]+", " ", expected.lower()).strip()
    norm_pdf = _re.sub(r"[^a-z0-9]+", " ", pdf_title.lower()).strip()
    if not norm_expected or not norm_pdf:
        return False
    if norm_expected == norm_pdf:
        return True
    if len(norm_expected) > 10 and len(norm_pdf) > 10:
        shorter = norm_expected if len(norm_expected) <= len(norm_pdf) else norm_pdf
        longer = norm_pdf if len(norm_expected) <= len(norm_pdf) else norm_expected
        if shorter in longer:
            return True
    # Token overlap check for fuzzy match
    expected_tokens = set(norm_expected.split())
    actual_tokens = set(norm_pdf.split())
    if expected_tokens and actual_tokens:
        overlap = len(expected_tokens & actual_tokens) / len(expected_tokens)
        if overlap >= 0.7:
            return True
    return False
