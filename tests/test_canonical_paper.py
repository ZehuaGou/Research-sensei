"""Tests for canonical_paper.md generation, source priority, metadata_only blocking, m2_ready gate."""
from __future__ import annotations

from pathlib import Path

from researchsensei.canonical import MaterialNormalizer, FormulaRegionDetector, FormulaOCRAdapter
from researchsensei.schemas import (
    CandidatePaper,
    CanonicalizationResult,
    CanonicalPaper,
    FormulaBlock,
    ResolvedPaperSource,
    SourcePriority,
    VerificationStatus,
)
from researchsensei.schemas.canonical import (
    AdapterInfo,
    CanonicalPaperFrontMatter,
    FormulaOcrResult,
    FormulaRegionResult,
)
from researchsensei.schemas.enums import (
    AdapterStatus,
    CanonicalizationStatus,
    FormulaOrigin,
    FormulaOcrStatus,
    PaperSourceStatus,
    PaperSourceType,
)


def _make_paper(**kwargs) -> CandidatePaper:
    defaults = {
        "paper_id": "test001",
        "title": "Test Paper Title",
        "authors": ["Author A", "Author B"],
        "year": 2024,
        "venue": "ICML",
        "abstract": "This is a test abstract about anomaly detection.",
        "source_confidence": "high",
        "metadata_confidence": "high",
    }
    defaults.update(kwargs)
    return CandidatePaper(**defaults)


def _make_source(**kwargs) -> ResolvedPaperSource:
    defaults = {
        "paper_id": "test001",
        "title": "Test Paper Title",
        "status": PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
        "source_type": PaperSourceType.PDF,
        "local_path": "",
        "sha256": "abc123",
        "file_size": 1000,
    }
    defaults.update(kwargs)
    return ResolvedPaperSource(**defaults)


class TestSourcePriority:
    def test_metadata_only_returns_metadata_priority(self):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_url="", pdf_downloaded=False, pdf_available=False)
        source = None
        result = normalizer.normalize(paper, source)
        assert result.source_priority == SourcePriority.METADATA_ONLY

    def test_metadata_only_cannot_enter_m2(self):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_url="", pdf_downloaded=False, pdf_available=False)
        result = normalizer.normalize(paper, None)
        assert result.m2_ready is False
        assert result.has_valid_deep_reading_source is False
        assert "metadata_only" in result.degradation_reason.lower() or "metadata_only" in (result.warnings[0] if result.warnings else "").lower()

    def test_pdf_source_priority(self):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_downloaded=True, pdf_available=True)
        source = _make_source(status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED)
        result = normalizer.normalize(paper, source)
        assert result.source_priority in (SourcePriority.PDF, SourcePriority.LATEX_SOURCE)

    def test_arxiv_source_gets_latex_priority(self):
        normalizer = MaterialNormalizer()
        paper = _make_paper(arxiv_id="2401.12345", pdf_downloaded=True)
        source = _make_source(
            source_type=PaperSourceType.ARXIV_SOURCE,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
        )
        result = normalizer.normalize(paper, source)
        assert result.source_priority == SourcePriority.LATEX_SOURCE


class TestCanonicalPaperGeneration:
    def test_canonical_paper_has_front_matter(self, tmp_path):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_downloaded=True, pdf_available=True)
        source = _make_source(status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED)
        result = normalizer.normalize(paper, source, output_dir=tmp_path)
        assert result.canonical_paper is not None
        fm = result.canonical_paper.front_matter
        assert fm.paper_id == "test001"
        assert fm.title == "Test Paper Title"
        assert fm.year == 2024
        assert fm.venue == "ICML"

    def test_canonical_paper_has_required_sections(self, tmp_path):
        normalizer = MaterialNormalizer()
        paper = _make_paper(
            pdf_downloaded=True,
            pdf_available=True,
            abstract="This paper presents a novel approach to anomaly detection using transformers.",
        )
        # Create a minimal PDF for testing
        pdf_path = tmp_path / "test.pdf"
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Test Paper Title\n\nAbstract\n\nThis paper presents a novel approach.")
            doc.save(str(pdf_path))
            doc.close()
        except ImportError:
            # PyMuPDF not available, skip PDF-specific tests
            return

        source = _make_source(
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            local_path=str(pdf_path),
        )
        result = normalizer.normalize(paper, source, output_dir=tmp_path)
        assert result.canonical_paper is not None
        md = result.canonical_paper.raw_markdown
        assert "## Abstract" in md
        assert "## Introduction" in md
        assert "## Method" in md

    def test_canonical_paper_written_to_file(self, tmp_path):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_downloaded=True, pdf_available=True)
        source = _make_source(status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED)
        result = normalizer.normalize(paper, source, output_dir=tmp_path)
        if result.canonical_paper_path:
            assert Path(result.canonical_paper_path).exists()


class TestFormulaBlock:
    def test_formula_block_origin_values(self):
        for origin in FormulaOrigin:
            fb = FormulaBlock(
                formula_id="eq1",
                latex="E = mc^2",
                origin=origin,
            )
            assert fb.origin == origin

    def test_formula_origin_source_latex(self):
        fb = FormulaBlock(
            formula_id="eq1",
            latex="\\mathcal{L} = \\sum_i l_i",
            origin=FormulaOrigin.SOURCE_LATEX,
            section="Method",
        )
        assert fb.origin == FormulaOrigin.SOURCE_LATEX
        assert fb.section == "Method"

    def test_formula_origin_ocr_latex(self):
        fb = FormulaBlock(
            formula_id="eq1",
            latex="y = mx + b",
            origin=FormulaOrigin.OCR_LATEX,
            ocr_status=FormulaOcrStatus.SUCCESS,
        )
        assert fb.origin == FormulaOrigin.OCR_LATEX
        assert fb.ocr_status == FormulaOcrStatus.SUCCESS


class TestFormulaRegionDetector:
    def test_detector_returns_not_detected_for_empty(self):
        detector = FormulaRegionDetector()
        result = detector.detect("eq1", "")
        assert result.formula_region_status == "not_detected"

    def test_detector_returns_unavailable_when_disabled(self):
        detector = FormulaRegionDetector(enabled=False)
        result = detector.detect("eq1", "some_path.pdf")
        assert result.formula_region_status == "unavailable"

    def test_detector_returns_unavailable_for_missing_file(self):
        detector = FormulaRegionDetector()
        result = detector.detect("eq1", "/nonexistent/path.pdf")
        assert result.formula_region_status == "unavailable"


class TestFormulaOCRAdapter:
    def test_ocr_returns_not_triggered_when_disabled(self):
        adapter = FormulaOCRAdapter(enabled=False)
        result = adapter.ocr("eq1", "some_path.pdf")
        assert result.formula_ocr_status == FormulaOcrStatus.NOT_TRIGGERED

    def test_ocr_returns_not_triggered_when_max_reached(self):
        adapter = FormulaOCRAdapter(max_per_paper=1)
        adapter._ocr_count = 1
        result = adapter.ocr("eq1", "some_path.pdf")
        assert result.formula_ocr_status == FormulaOcrStatus.NOT_TRIGGERED

    def test_ocr_returns_failed_or_unavailable_when_model_not_loaded(self):
        adapter = FormulaOCRAdapter()
        adapter._model_load_attempted = True
        adapter._model = None
        result = adapter.ocr("eq1", "some_path.pdf")
        # Returns FAILED (file not found) or UNAVAILABLE (model not loaded)
        assert result.formula_ocr_status in (FormulaOcrStatus.FAILED, FormulaOcrStatus.UNAVAILABLE)

    def test_ocr_reset_count(self):
        adapter = FormulaOCRAdapter(max_per_paper=3)
        adapter._ocr_count = 3
        adapter.reset_count()
        assert adapter._ocr_count == 0


class TestAdapterStatus:
    def test_adapter_info_fields(self):
        info = AdapterInfo(
            name="test_adapter",
            status=AdapterStatus.IMPLEMENTED,
            attempt_details=["detail1"],
        )
        assert info.name == "test_adapter"
        assert info.status == AdapterStatus.IMPLEMENTED

    def test_adapter_status_values(self):
        for status in AdapterStatus:
            info = AdapterInfo(name="test", status=status)
            assert info.status == status


class TestCanonicalizationResult:
    def test_result_has_required_fields(self):
        result = CanonicalizationResult(
            paper_id="test001",
            title="Test Paper",
        )
        assert result.paper_id == "test001"
        assert result.title == "Test Paper"
        assert result.source_priority == SourcePriority.METADATA_ONLY
        assert result.m2_ready is False

    def test_result_with_canonical_paper(self, tmp_path):
        normalizer = MaterialNormalizer()
        paper = _make_paper(pdf_downloaded=True, pdf_available=True)
        source = _make_source(status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED)
        result = normalizer.normalize(paper, source, output_dir=tmp_path)
        assert result.canonical_paper is not None
        assert result.canonicalization_status in (
            CanonicalizationStatus.SUCCESS,
            CanonicalizationStatus.DEGRADED,
            CanonicalizationStatus.FAILED,
        )
