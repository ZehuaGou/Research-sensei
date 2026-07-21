from __future__ import annotations

from pathlib import Path

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.mineru25_adapter import FormulaRegionCandidate
from researchsensei.ingestion.mineru_enhanced import MineruEnhancedIngestionService
from researchsensei.schemas import BlockType


class FakeMineruAdapter:
    def __init__(self, *, available: bool = True, device: str = "cuda", fail: bool = False) -> None:
        self.available = available
        self.device = device
        self.fail = fail

    def is_available(self) -> bool:
        return self.available

    def _probe_device(self) -> dict[str, str]:
        return {"device_mode_actual": self.device}

    def parse_formula_regions(self, _path, regions, *, progress=None):
        if self.fail:
            raise RuntimeError("synthetic parser failure")
        if progress:
            progress(1, 1)
        region: FormulaRegionCandidate = regions[0]
        return (
            [
                CanonicalDocumentBlock(
                    block_id="mineru_eq_001",
                    page=region.page,
                    bbox=list(region.bbox),
                    block_type="formula",
                    latex=r"L=\frac{1}{N}\sum_i e_i^2\tag{4}",
                    reading_order=1,
                    source="mineru25pro",
                    section=region.section,
                    section_confidence="high",
                    raw_payload_ref="formula_region_001",
                )
            ],
            {"stats": {"device_mode_actual": "cuda"}},
        )


def _minimal_pdf(path: Path) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "4 Methodology")
    page.insert_text((72, 105), "We minimize the prediction error.")
    page.insert_text((72, 145), "L = 1/N sum e_i^2")
    page.insert_text((280, 145), "(4)")
    page.insert_text((72, 190), "This loss trains the forecasting network.")
    document.save(path)
    document.close()


def test_mineru_pdf_blocks_preserve_formula_provenance_and_context(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    _minimal_pdf(source)
    stages: list[tuple[str, int]] = []
    service = MineruEnhancedIngestionService(adapter=FakeMineruAdapter())  # type: ignore[arg-type]

    document = service.ingest_path(
        source,
        paper_id="paper-1",
        progress=lambda stage, value: stages.append((stage, value)),
    )

    assert document.parser_name == "pymupdf+mineru_formula_regions"
    assert document.degraded is False
    formula = next(block for block in document.blocks if block.type == BlockType.FORMULA)
    assert formula.formula_origin == "mineru_latex"
    assert formula.formula_ocr_status == "not_required"
    assert formula.formula_explanation_status == "parser_derived"
    assert formula.formula_page == 1
    assert formula.formula_bbox is not None
    assert formula.equation_number == "4"
    assert "prediction error" in formula.formula_context_before
    assert "forecasting network" in formula.formula_context_after
    assert formula.evidence_ref == "paper-1:mineru_eq_001"
    assert ("detecting_formula_regions", 21) in stages
    assert ("loading_formula_parser", 22) in stages
    assert ("parsing_formula_regions:1/1", 30) in stages


def test_mineru_failure_falls_back_without_trusting_raw_formula_text(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    _minimal_pdf(source)
    service = MineruEnhancedIngestionService(
        adapter=FakeMineruAdapter(fail=True),  # type: ignore[arg-type]
    )

    document = service.ingest_path(source, paper_id="paper-2")

    assert document.parser_name == "pymupdf_lightweight"
    assert document.degraded is True
    assert any(warning.code == "MINERU_PARSE_FAILED" for warning in document.warnings)
    assert all(block.formula_origin != "mineru_latex" for block in document.blocks)


def test_mineru_cpu_route_falls_back_before_model_load(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    _minimal_pdf(source)
    service = MineruEnhancedIngestionService(
        adapter=FakeMineruAdapter(device="cpu"),  # type: ignore[arg-type]
    )

    document = service.ingest_path(source, paper_id="paper-3")

    assert document.degraded is True
    assert any(warning.code == "MINERU_CUDA_REQUIRED" for warning in document.warnings)


def test_default_interactive_service_disables_slow_cpu_model_fallback() -> None:
    service = MineruEnhancedIngestionService()

    assert service.require_cuda is True
    assert service.adapter.allow_cpu_fallback is False
