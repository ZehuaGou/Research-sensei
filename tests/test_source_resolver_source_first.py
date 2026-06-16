from __future__ import annotations

import io
import tarfile
from pathlib import Path

from researchsensei.source_resolver import SourceResolver, select_latex_main_file


class StubHttpResponse:
    def __init__(self, content: bytes, *, content_type: str, url: str = "https://arxiv.org/e-print/2401.00001") -> None:
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.url = url

    def raise_for_status(self) -> None:
        return None


class SourceFirstHttpClient:
    def __init__(self, source_content: bytes, pdf_content: bytes = b"%PDF-1.4 fake pdf") -> None:
        self.source_content = source_content
        self.pdf_content = pdf_content
        self.urls: list[str] = []

    def get(self, url: str, **kwargs) -> StubHttpResponse:
        self.urls.append(url)
        if "/e-print/" in url:
            return StubHttpResponse(self.source_content, content_type="application/x-gzip", url=url)
        return StubHttpResponse(self.pdf_content, content_type="application/pdf", url=url)


class FallbackHttpClient(SourceFirstHttpClient):
    def get(self, url: str, **kwargs) -> StubHttpResponse:
        self.urls.append(url)
        if "/e-print/" in url:
            raise RuntimeError("source unavailable")
        return StubHttpResponse(self.pdf_content, content_type="application/pdf", url=url)


def test_arxiv_source_url_generation() -> None:
    assert SourceResolver.arxiv_to_source_url(arxiv_id="2401.00001") == "https://arxiv.org/e-print/2401.00001"
    assert SourceResolver.arxiv_to_source_url(arxiv_url="https://arxiv.org/abs/2401.00001v2") == "https://arxiv.org/e-print/2401.00001v2"


def test_arxiv_source_download_success_prefers_latex(tmp_path: Path) -> None:
    http_client = SourceFirstHttpClient(_tar_source({"main.tex": _latex_text()}))
    resolver = SourceResolver(http_client=http_client)

    status = resolver.resolve_arxiv_id("2401.00001", tmp_path)

    assert status.status == "resolved"
    assert status.source_type == "arxiv_source"
    assert status.preferred_m2_input == "latex_source"
    assert status.source_priority == "latex_source"
    assert status.latex_source_available is True
    assert status.latex_source_path.endswith("main.tex")
    assert Path(status.source_manifest_path).exists()
    assert http_client.urls == ["https://arxiv.org/e-print/2401.00001"]


def test_arxiv_source_unavailable_falls_back_to_pdf(tmp_path: Path) -> None:
    http_client = FallbackHttpClient(b"", pdf_content=b"%PDF-1.4 fallback pdf")
    resolver = SourceResolver(http_client=http_client)

    status = resolver.resolve_arxiv_id("2401.00001", tmp_path)

    assert status.status == "resolved"
    assert status.source_type == "arxiv_pdf"
    assert status.preferred_m2_input == "pdf"
    assert status.source_strategy == "pdf_fallback"
    assert status.fallback_used == "source_unavailable"
    assert status.warnings[:2] == ["ARXIV_SOURCE_UNAVAILABLE", "source_unavailable"]
    assert http_client.urls == [
        "https://arxiv.org/e-print/2401.00001",
        "https://arxiv.org/pdf/2401.00001.pdf",
    ]


def test_select_latex_main_file_prefers_documentclass(tmp_path: Path) -> None:
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections" / "appendix.tex").write_text("appendix " * 100, encoding="utf-8")
    main = tmp_path / "paper.tex"
    main.write_text("\\documentclass{article}\\begin{document}Main\\end{document}", encoding="utf-8")

    selected, reason = select_latex_main_file(tmp_path)

    assert selected == main
    assert reason == "documentclass"


def _tar_source(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _latex_text() -> str:
    return r"""
\documentclass{article}
\title{Tiny Source Paper}
\begin{document}
\begin{abstract}
We study time series anomaly detection.
\end{abstract}
\section{Methodology}
Our approach uses a reconstruction model.
\begin{equation}
L = L_{rec} + \lambda L_{graph}
\end{equation}
\section{Experiments}
We evaluate on benchmark datasets.
\end{document}
"""
