from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

import httpx

from researchsensei.schemas import SourceStatus

logger = logging.getLogger(__name__)


SUPPORTED_LOCAL_SUFFIXES = {".md", ".txt", ".pdf"}
PDF_BYTES = b"%PDF"


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


def _content_type_for_suffix(suffix: str) -> str:
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
    }.get(suffix, "")
