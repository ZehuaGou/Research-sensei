from __future__ import annotations

from pathlib import Path

import pytest

from researchsensei.ingestion import LightweightIngestionService
from researchsensei.schemas import BlockType


def test_ingests_markdown_into_heading_paragraph_and_formula_blocks(tmp_path: Path) -> None:
    path = tmp_path / "paper.md"
    path.write_text(
        """
# Tiny Paper
## Abstract
We study anomaly detection in multivariate time series.

## Method
We minimize L = L_rec + lambda L_graph to model sensor dependencies.

## Experiments
Table 1 reports better F1.
""".strip(),
        encoding="utf-8",
    )

    doc = LightweightIngestionService().ingest_path(path, paper_id="paper-md")

    assert doc.paper_id == "paper-md"
    assert doc.source_path == str(path)
    assert doc.degraded is False
    assert any(block.type == BlockType.HEADING and block.section == "method" for block in doc.blocks)
    assert any(block.type == BlockType.PARAGRAPH for block in doc.blocks)
    assert any(block.type == BlockType.FORMULA and block.evidence_ref == "paper-md:eq001" for block in doc.blocks)
    assert all(warning.code != "FORMULA_UNAVAILABLE" for warning in doc.warnings)


def test_ingests_txt_and_detects_chinese_language(tmp_path: Path) -> None:
    path = tmp_path / "paper.txt"
    path.write_text("摘要\n这是一个时间序列异常检测方法。\n方法\n我们使用重构误差。", encoding="utf-8")

    doc = LightweightIngestionService().ingest_path(path, paper_id="paper-txt")

    assert doc.detected_language == "zh"
    assert doc.blocks
    assert doc.blocks[0].evidence_ref.startswith("paper-txt:")


def test_invalid_pdf_degrades_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a valid pdf")

    doc = LightweightIngestionService().ingest_path(path, paper_id="paper-pdf")

    assert doc.degraded is True
    assert any(warning.code == "PDF_PARSE_FAILED" for warning in doc.warnings)


def test_valid_pdf_extracts_text_when_pymupdf_is_available(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "paper.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Abstract\nWe study anomaly detection in time series.")
    pdf.save(path)
    pdf.close()

    doc = LightweightIngestionService().ingest_path(path, paper_id="paper-pdf")

    assert doc.degraded is False
    assert any("anomaly detection" in block.text for block in doc.blocks)
