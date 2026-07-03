from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

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

    def resolve_many(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        download_dir: str | Path | None = None,
    ) -> SourceResolutionResult:
        actual_download_dir = Path(download_dir).resolve() if download_dir else self.download_dir
        items = [self.resolve_one(candidate, download_dir=actual_download_dir) for candidate in candidates]
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
        pdf_url = paper.pdf_url
        landing_url = paper.landing_url or paper.url or _doi_url(paper.doi)
        source_type = PaperSourceType.PDF if pdf_url else PaperSourceType.METADATA_ONLY

        if paper.arxiv_id:
            arxiv_pdf = SourceResolver.arxiv_to_pdf_url(arxiv_id=paper.arxiv_id)
            pdf_url = pdf_url or arxiv_pdf
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
                    return source_result

        if pdf_url:
            if self.network_enabled and (download_dir or self.download_dir):
                return self._download_pdf(
                    paper,
                    pdf_url=pdf_url,
                    source_url=source_url or pdf_url,
                    landing_url=landing_url,
                    source_type=source_type,
                    download_dir=Path(download_dir or self.download_dir),  # type: ignore[arg-type]
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

        paper_dir = download_dir / _safe_name(paper.paper_id or paper.title)
        paper_dir.mkdir(parents=True, exist_ok=True)
        target = paper_dir / "source.pdf"
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
        paper_dir = download_dir / _safe_name(paper.paper_id or paper.title)
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
        try:
            response = self.http_client.get(source_url, timeout=self.timeout_seconds, follow_redirects=True)
            response.raise_for_status()
        except Exception as exc:
            logger.info("arXiv source download failed for %s, falling back to PDF: %s", arxiv_id, exc)
            self._last_arxiv_source_fallback = "source_unavailable"
            return None

        content = response.content
        content_length = int(response.headers.get("content-length") or len(content))
        content_type = response.headers.get("content-type", "")
        if content_length > self.max_download_bytes or len(content) > self.max_download_bytes:
            logger.warning("arXiv source %s exceeds configured size limit; falling back to PDF.", arxiv_id)
            self._last_arxiv_source_fallback = "source_unavailable"
            return None
        if not content or content.startswith(PDF_BYTES) or "pdf" in content_type.lower():
            logger.info("arXiv source endpoint for %s did not return LaTeX source; falling back to PDF.", arxiv_id)
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
    clean = doi.strip()
    if not clean:
        return ""
    if clean.lower().startswith(("http://", "https://")):
        return clean
    clean = clean.removeprefix("doi:").removeprefix("DOI:")
    return f"https://doi.org/{clean}"


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

    documentclass_matches: list[Path] = []
    for path in tex_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "\\documentclass" in text:
            documentclass_matches.append(path)
    if documentclass_matches:
        documentclass_matches.sort(key=lambda path: path.stat().st_size, reverse=True)
        return documentclass_matches[0], "documentclass"

    tex_files.sort(key=lambda path: path.stat().st_size, reverse=True)
    return tex_files[0], "largest_tex"


def _unique_warnings(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "paper"


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
