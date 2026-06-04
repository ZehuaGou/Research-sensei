from __future__ import annotations

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
    """M1.3 resolver for candidate-paper source material metadata.

    This resolver does not download or parse paper content. It only records
    source URLs, fallback status, warnings, and metadata needed by later modules.
    """

    def __init__(
        self,
        *,
        network_enabled: bool = False,
        external_resolver: Callable[[CandidatePaper], ResolvedPaperSource | None] | None = None,
    ) -> None:
        self.network_enabled = network_enabled
        self.external_resolver = external_resolver

    def resolve_many(self, query: str, candidates: list[CandidatePaper]) -> SourceResolutionResult:
        items = [self.resolve_one(candidate) for candidate in candidates]
        warnings: list[WarningItem] = []
        if any(item.status in {PaperSourceStatus.PARTIAL, PaperSourceStatus.NOT_FOUND, PaperSourceStatus.FAILED} for item in items):
            warnings.append(
                WarningItem(
                    code="PARTIAL_SOURCE_RESOLUTION",
                    message="Some candidate papers could not be fully resolved to source material.",
                )
            )
        return SourceResolutionResult(query=query, items=items, warnings=warnings)

    def resolve_one(self, paper: CandidatePaper) -> ResolvedPaperSource:
        try:
            if self.network_enabled and self.external_resolver is not None:
                resolved = self.external_resolver(paper)
                if resolved is not None:
                    return resolved
        except Exception as exc:
            logger.warning("M1 paper source resolver failed for %s: %s", paper.paper_id, exc)
            return self._base_result(
                paper,
                status=PaperSourceStatus.FAILED,
                source_type=PaperSourceType.METADATA_ONLY,
                warnings=[WarningItem(code="RESOLVER_FAILED", message="External source resolver failed.")],
                error=str(exc)[:300],
            )

        if paper.arxiv_id:
            pdf_url = SourceResolver.arxiv_to_pdf_url(arxiv_id=paper.arxiv_id)
            source_url = self.arxiv_to_source_url(paper.arxiv_id)
            if source_url and pdf_url:
                metadata = {"resolution_strategy": "arxiv_source_first"}
                if paper.pdf_url and paper.pdf_url != pdf_url:
                    metadata["fallback_pdf_url"] = paper.pdf_url
                return self._base_result(
                    paper,
                    status=PaperSourceStatus.RESOLVED,
                    source_type=PaperSourceType.ARXIV_SOURCE,
                    source_url=source_url,
                    pdf_url=pdf_url,
                    landing_url=paper.url or self.arxiv_to_abs_url(paper.arxiv_id),
                    metadata=metadata,
                )

        if paper.pdf_url:
            return self._base_result(
                paper,
                status=PaperSourceStatus.RESOLVED,
                source_type=PaperSourceType.PDF,
                pdf_url=paper.pdf_url,
                landing_url=paper.url or _doi_url(paper.doi),
                source_url=paper.pdf_url,
                metadata={"resolution_strategy": "candidate_pdf_url"},
            )

        explicit_landing_url = bool(paper.url)
        landing_url = paper.url or _doi_url(paper.doi)
        if landing_url:
            warnings = [WarningItem(code="PDF_URL_MISSING", message="No PDF URL is available for this candidate.")]
            if not self.network_enabled:
                network_warning = WarningItem(code="NETWORK_DISABLED", message="Network resolver is disabled.")
                if explicit_landing_url:
                    warnings.append(network_warning)
                else:
                    warnings.insert(0, network_warning)
            return self._base_result(
                paper,
                status=PaperSourceStatus.PARTIAL,
                source_type=PaperSourceType.LANDING_PAGE,
                landing_url=landing_url,
                warnings=warnings,
                metadata={"resolution_strategy": "landing_page_only"},
            )

        return self._base_result(
            paper,
            status=PaperSourceStatus.NOT_FOUND,
            source_type=PaperSourceType.METADATA_ONLY,
            warnings=[
                WarningItem(code="NO_SOURCE_URL", message="No source, landing, DOI, arXiv, or PDF URL found."),
                WarningItem(code="PDF_URL_MISSING", message="No PDF URL is available for this candidate."),
            ],
            metadata={"resolution_strategy": "metadata_only"},
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
        warnings: list[WarningItem] | None = None,
        error: str = "",
        metadata: dict[str, str] | None = None,
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
            warnings=warnings or [],
            error=error,
            metadata=metadata or {},
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
