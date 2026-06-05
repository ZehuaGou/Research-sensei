from __future__ import annotations

import hashlib
import logging
import re
import shutil
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

from researchsensei.schemas import (
    CandidatePaper,
    PaperSourceStatus,
    PaperSourceType,
    ResolvedPaperSource,
    SourceResolutionResult,
    SourceStatus,
    WarningItem,
)

logger = logging.getLogger(__name__)

SUPPORTED_LOCAL_SUFFIXES = {".md", ".txt", ".pdf"}
PDF_BYTES = b"%PDF"


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
        if any(item.status != PaperSourceStatus.RESOLVED_PDF_DOWNLOADED for item in items):
            warnings.append(
                WarningItem(
                    code="PARTIAL_SOURCE_RESOLUTION",
                    message="Some candidates were not downloaded as validated PDFs.",
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
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
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
    ) -> ResolvedPaperSource:
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
        )

    def resolve_arxiv_id(self, arxiv_id: str, run_dir: str | Path) -> SourceStatus:
        pdf_url = self.arxiv_to_pdf_url(arxiv_id=arxiv_id)
        if not pdf_url:
            return _status(
                source_type="arxiv_id",
                original_input=arxiv_id,
                status="rejected",
                warnings=["INVALID_ARXIV_ID"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )
        status = self.resolve_pdf_url(pdf_url, run_dir)
        return status.model_copy(update={"source_type": "arxiv_id", "original_input": arxiv_id})

    def resolve_arxiv_url(self, arxiv_url: str, run_dir: str | Path) -> SourceStatus:
        pdf_url = self.arxiv_to_pdf_url(arxiv_url=arxiv_url)
        if not pdf_url:
            return _status(
                source_type="arxiv_url",
                original_input=arxiv_url,
                status="rejected",
                warnings=["INVALID_ARXIV_ID"],
                degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
            )
        status = self.resolve_pdf_url(pdf_url, run_dir)
        return status.model_copy(update={"source_type": "arxiv_url", "original_input": arxiv_url})

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
    )


def _is_valid_arxiv_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", value))


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
    }.get(suffix, "")


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "paper"


def _check_pdf_metadata(content: bytes, expected_title: str) -> tuple[str, str, str]:
    """M1.3 lightweight PDF metadata validation.

    Returns (pdf_metadata_check, pdf_title_match, pdf_metadata_warning).
    Only examines the first 64KB for PDF /Title metadata — not full parsing.
    """
    if not expected_title:
        return ("skipped", "unknown", "No expected title to compare against.")

    # Check %PDF header (already validated by caller, but be explicit)
    if not content.startswith(PDF_BYTES):
        return ("failed", "unknown", "Content does not start with %PDF header.")

    # Look for /Title in first 64KB of PDF (common metadata location)
    header_chunk = content[: 64 * 1024]
    try:
        header_text = header_chunk.decode("latin-1", errors="ignore")
    except Exception:
        return ("passed", "unknown", "Could not decode PDF header for metadata check.")

    title_match = _extract_pdf_title_from_header(header_text)
    if title_match is None:
        return ("passed", "unknown", "No /Title metadata found in PDF header.")

    match_result = "match" if _titles_match_for_pdf(expected_title, title_match) else "mismatch"
    warning = "" if match_result == "match" else f"PDF /Title '{title_match[:80]}' does not match expected title."
    return ("passed", match_result, warning)


def _extract_pdf_title_from_header(header_text: str) -> str | None:
    """Extract /Title from PDF metadata header section."""
    # Match /Title (...) or /Title <hex>
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
    return False
