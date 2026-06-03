from __future__ import annotations

from pathlib import Path

import httpx

from researchsensei.source_resolver import SourceResolver


def _pdf_response(content: bytes = b"%PDF-1.4\nminimal") -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/pdf", "content-length": str(len(content))},
        content=content,
    )


def test_resolve_local_txt_copies_file_inside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    run_dir = tmp_path / "run"
    allowed.mkdir()
    source = allowed / "paper.txt"
    source.write_text("Abstract\nA local paper.", encoding="utf-8")

    status = SourceResolver(allowed_roots=[allowed]).resolve_local_path(source, run_dir=run_dir)

    assert status.status == "resolved"
    assert status.source_type == "local_path"
    assert Path(status.resolved_path).read_text(encoding="utf-8") == "Abstract\nA local paper."
    assert Path(status.resolved_path).parent == run_dir
    assert status.size_bytes > 0


def test_resolve_local_md_copies_file_inside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    run_dir = tmp_path / "run"
    allowed.mkdir()
    source = allowed / "paper.md"
    source.write_text("# Paper", encoding="utf-8")

    status = SourceResolver(allowed_roots=[allowed]).resolve_local_path(source, run_dir=run_dir)

    assert status.status == "resolved"
    assert status.resolved_path.endswith("source.md")


def test_resolve_local_path_outside_allowed_root_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "secret.txt"
    source.write_text("secret", encoding="utf-8")

    status = SourceResolver(allowed_roots=[allowed]).resolve_local_path(source, run_dir=tmp_path / "run")

    assert status.status == "rejected"
    assert "SECURITY_REJECTED" in status.warnings
    assert not status.resolved_path


def test_resolve_local_path_traversal_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "secret.txt"
    source.write_text("secret", encoding="utf-8")
    traversal = allowed / ".." / "outside" / "secret.txt"

    status = SourceResolver(allowed_roots=[allowed]).resolve_local_path(traversal, run_dir=tmp_path / "run")

    assert status.status == "rejected"
    assert "SECURITY_REJECTED" in status.warnings


def test_download_pdf_url_success_uses_mocked_network(tmp_path: Path) -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _pdf_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    status = SourceResolver(http_client=client).resolve_pdf_url("https://example.com/paper.pdf", tmp_path)

    assert status.status == "resolved"
    assert seen_urls == ["https://example.com/paper.pdf"]
    assert status.content_type == "application/pdf"
    assert status.size_bytes > 0
    assert Path(status.resolved_path).read_bytes().startswith(b"%PDF")


def test_download_pdf_url_failure_marks_download_failed(tmp_path: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404)))

    status = SourceResolver(http_client=client).resolve_pdf_url("https://example.com/missing.pdf", tmp_path)

    assert status.status == "failed"
    assert "DOWNLOAD_FAILED" in status.warnings
    assert "FULL_TEXT_MISSING" in status.degraded_flags


def test_download_pdf_url_rejects_oversized_response(tmp_path: Path) -> None:
    content = b"%PDF" + (b"x" * 20)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: _pdf_response(content)))

    status = SourceResolver(http_client=client, max_download_bytes=10).resolve_pdf_url(
        "https://example.com/large.pdf",
        tmp_path,
    )

    assert status.status == "rejected"
    assert "DOWNLOAD_TOO_LARGE" in status.warnings
    assert not status.resolved_path


def test_download_pdf_url_rejects_non_pdf_content(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html></html>")
        )
    )

    status = SourceResolver(http_client=client).resolve_pdf_url("https://example.com/not-pdf", tmp_path)

    assert status.status == "rejected"
    assert "UNSUPPORTED_SOURCE" in status.warnings
    assert "FULL_TEXT_MISSING" in status.degraded_flags


def test_pdf_url_rejects_unsupported_scheme(tmp_path: Path) -> None:
    status = SourceResolver().resolve_pdf_url("file:///secret.pdf", tmp_path)

    assert status.status == "rejected"
    assert "UNSUPPORTED_SOURCE" in status.warnings


def test_arxiv_id_converts_to_pdf_url() -> None:
    assert SourceResolver.arxiv_to_pdf_url(arxiv_id="2301.12345v2") == "https://arxiv.org/pdf/2301.12345v2.pdf"
    assert SourceResolver.arxiv_to_pdf_url(arxiv_id="arXiv:2301.12345") == "https://arxiv.org/pdf/2301.12345.pdf"


def test_arxiv_urls_convert_to_pdf_url() -> None:
    resolver = SourceResolver

    assert resolver.arxiv_to_pdf_url(arxiv_url="https://arxiv.org/abs/2301.12345") == (
        "https://arxiv.org/pdf/2301.12345.pdf"
    )
    assert resolver.arxiv_to_pdf_url(arxiv_url="https://arxiv.org/pdf/2301.12345.pdf") == (
        "https://arxiv.org/pdf/2301.12345.pdf"
    )
