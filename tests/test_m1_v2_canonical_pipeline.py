from __future__ import annotations

import inspect
from pathlib import Path

from researchsensei.schemas.enums import CanonicalQualityStatus, FormulaOrigin


def _block(
    block_id: str,
    *,
    page: int,
    block_type: str = "text",
    text: str = "",
    latex: str = "",
    bbox: list[float] | None = None,
    section: str = "",
):
    from researchsensei.canonical.document_blocks import CanonicalDocumentBlock

    return CanonicalDocumentBlock(
        block_id=block_id,
        page=page,
        bbox=bbox or [10, 20, 110, 40],
        block_type=block_type,
        text=text,
        latex=latex,
        reading_order=int(block_id.strip("b") or 0),
        source="mineru25pro",
        section=section,
    )


def _reviewed_slots(blocks) -> list[dict]:
    slots = []
    for index, block in enumerate((b for b in blocks if b.block_type == "formula"), start=1):
        slots.append({
            "formula_id": f"formula_{index:03d}",
            "block_id": block.block_id,
            "page": block.page,
            "bbox": block.bbox,
            "crop_required": True,
            "overlay_required": True,
            "crop_path": f"formula_crops/{block.block_id}.png",
            "overlay_path": f"formula_overlays/{block.block_id}.png",
            "source_mismatch": False,
        })
    return slots


def test_document_block_normalizes_type_bbox_and_identity() -> None:
    from researchsensei.canonical.document_blocks import CanonicalDocumentBlock

    block = CanonicalDocumentBlock(
        block_id="b001",
        page=0,
        bbox=["1", 2, 3.5, "4.25"],
        block_type="equation",
        latex="E=mc^2",
        source="mineru25pro",
    )

    assert block.page == 1
    assert block.bbox == [1.0, 2.0, 3.5, 4.25]
    assert block.block_type == "formula"
    assert block.identity_key == ("b001", 1, (1.0, 2.0, 3.5, 4.25), "mineru25pro")


def test_document_block_normalizes_parser_null_strings() -> None:
    from researchsensei.canonical.document_blocks import CanonicalDocumentBlock

    block = CanonicalDocumentBlock(
        block_id="b-null",
        page=1,
        bbox=[0, 0, 1, 1],
        block_type="text",
        text=None,
        latex=None,
        html=None,
        source=None,
    )

    assert block.text == ""
    assert block.latex == ""
    assert block.html == ""
    assert block.source == ""


def test_mineru25_adapter_uses_mineru_vl_utils_not_magic_pdf() -> None:
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    source = inspect.getsource(MinerU25ProAdapter)

    assert "mineru_vl_utils" in source
    assert "magic_pdf" not in source


def test_mineru25_adapter_normalizes_mocked_output() -> None:
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter()
    blocks = adapter.normalize_page_result(
        [
            {"type": "title", "bbox": [1, 2, 100, 20], "content": "3 Method"},
            {"type": "equation", "bbox": [5, 30, 120, 55], "content": "$$x_t = f(h_t)$$"},
        ],
        page=4,
    )

    assert [b.block_type for b in blocks] == ["title", "formula"]
    assert blocks[1].latex == "x_t = f(h_t)"
    assert blocks[1].source == "mineru25pro"
    assert blocks[1].page == 4


def test_rule_based_refiner_assigns_formula_sections_from_timeline() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="Short abstract."),
        _block("b003", page=4, block_type="title", text="3 Method"),
        _block("b004", page=4, block_type="formula", latex="x_t=f(h_t)"),
        _block("b005", page=6, block_type="title", text="4 Experiments"),
        _block("b006", page=6, block_type="formula", latex="score=max_t e_t"),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert by_id["b004"].section == "Method"
    assert by_id["b004"].section_confidence in {"high", "medium"}
    assert by_id["b006"].section == "Experiments"
    assert "ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS" not in by_id["b004"].risk_flags


def test_quality_gate_blocks_all_formulas_in_abstract() -> None:
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block(f"b{i:03d}", page=i + 2, block_type="formula", latex=f"x_{i}=y", section="Abstract")
        for i in range(6)
    ]

    result = M1QualityGate().evaluate(blocks, formula_slots=[])

    assert result.status == CanonicalQualityStatus.FAIL
    assert result.all_formulas_in_abstract_suspicious is True
    assert "ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS" in result.blocking_reasons


def test_quality_gate_blocks_section_contradiction() -> None:
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block("b001", page=4, block_type="formula", latex="x=y", section="Abstract"),
        _block("b002", page=4, block_type="title", text="3 Method", section="Method"),
    ]

    result = M1QualityGate().evaluate(blocks, formula_slots=[])

    assert result.status == CanonicalQualityStatus.FAIL
    assert result.section_contradiction_count == 1


def test_quality_gate_requires_crop_overlay_when_formula_slots_missing() -> None:
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [_block("b001", page=3, block_type="formula", latex="x=y", section="Method")]

    result = M1QualityGate().evaluate(blocks, formula_slots=[])

    assert result.status == CanonicalQualityStatus.FAIL
    assert result.missing_crop_count == 1
    assert result.missing_overlay_count == 1
    assert "MISSING_FORMULA_CROP" in result.blocking_reasons
    assert "MISSING_FORMULA_OVERLAY" in result.blocking_reasons


def test_quality_gate_marks_dense_raw_only_formulas_degraded_not_formula_ready() -> None:
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block(f"b{i:03d}", page=3, block_type="formula", text=f"raw formula line {i}: x{i}=y{i}", latex="", section="Method")
        for i in range(1, 6)
    ]

    result = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    assert result.status == CanonicalQualityStatus.DEGRADED
    assert result.m2_ready_for_formula_understanding is False
    assert result.raw_only_formula_dense is True
    assert result.high_risk_count >= 1
    assert "RAW_ONLY_FORMULA_DENSE_NO_LATEX" in result.warning_reasons


def test_ollama_client_uses_native_chat_json_schema(monkeypatch) -> None:
    from researchsensei.canonical.ollama_refiner import OllamaStructuredClient

    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"message": {"content": '{"assignments": []}'}}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    client = OllamaStructuredClient(model="qwen2.5:0.5b", timeout_seconds=3)
    payload = client.chat_json("assign sections", schema={"type": "object", "properties": {"assignments": {"type": "array"}}})

    assert payload == {"assignments": []}
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["temperature"] == 0
    assert captured["json"]["format"]["type"] == "object"


def test_ollama_invalid_json_is_noop_with_warning(monkeypatch) -> None:
    from researchsensei.canonical.ollama_refiner import OllamaSectionRefiner, OllamaStructuredClient

    blocks = [_block("b001", page=1, text="Abstract text", section="Abstract")]

    class BadClient(OllamaStructuredClient):
        def chat_json(self, prompt: str, schema: dict) -> dict | None:
            self.json_invalid_count += 1
            self.warnings.append("invalid_json")
            return None

    refiner = OllamaSectionRefiner(client=BadClient())
    refined = refiner.refine(blocks)

    assert refined[0].section == "Abstract"
    assert refiner.metrics.json_invalid_count == 1
    assert refiner.metrics.changed_by_count == 0
    assert refiner.metrics.warnings


def test_ollama_refiner_cannot_modify_latex_bbox_page_or_source() -> None:
    from researchsensei.canonical.ollama_refiner import OllamaSectionRefiner, OllamaStructuredClient

    blocks = [_block("b001", page=4, block_type="formula", latex="x=y", bbox=[1, 2, 3, 4], section="Method")]

    class MutatingClient(OllamaStructuredClient):
        def chat_json(self, prompt: str, schema: dict) -> dict | None:
            self.json_valid_count += 1
            return {
                "assignments": [
                    {
                        "block_id": "b001",
                        "section": "Experiments",
                        "latex": "MUTATED",
                        "bbox": [9, 9, 9, 9],
                        "page": 99,
                        "source": "ollama",
                    }
                ]
            }

    refiner = OllamaSectionRefiner(client=MutatingClient())
    refined = refiner.refine(blocks)
    block = refined[0]

    assert block.section == "Experiments"
    assert block.latex == "x=y"
    assert block.bbox == [1.0, 2.0, 3.0, 4.0]
    assert block.page == 4
    assert block.source == "mineru25pro"


def test_canonical_builder_v2_preserves_formula_identity_and_gate_status(tmp_path) -> None:
    from researchsensei.canonical.canonical_builder_v2 import CanonicalBuilderV2
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract", section="Abstract"),
        _block("b002", page=1, text="We study anomaly detection.", section="Abstract"),
        _block("b003", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
    ]
    gate = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    result = CanonicalBuilderV2().build(
        paper_id="p-test",
        title="A Test Paper",
        blocks=blocks,
        quality=gate,
        output_dir=tmp_path,
    )

    markdown = Path(result.canonical_paper_path).read_text(encoding="utf-8")
    assert result.canonical_quality_status == CanonicalQualityStatus.PASS
    assert "primary_parser: mineru25pro" in markdown
    assert "canonical_quality_status: PASS" in markdown
    assert "origin: mineru_latex" in markdown
    assert "x_t=f(h_t)" in markdown
    assert result.formula_blocks[0].origin == FormulaOrigin.MINERU_LATEX


def test_canonical_builder_blocks_m2_formula_understanding_for_raw_only_dense_formulas(tmp_path) -> None:
    from researchsensei.canonical.canonical_builder_v2 import CanonicalBuilderV2
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block(f"b{i:03d}", page=4, block_type="formula", text=f"raw-only formula {i}: score_t=max e_t", section="Method")
        for i in range(1, 6)
    ]
    quality = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    result = CanonicalBuilderV2().build(
        paper_id="p-raw-only",
        title="Raw Formula Paper",
        blocks=blocks,
        quality=quality,
        output_dir=tmp_path,
    )

    markdown = Path(result.canonical_paper_path).read_text(encoding="utf-8")
    assert result.canonical_quality_status == CanonicalQualityStatus.DEGRADED
    assert result.m2_ready is False
    assert result.m2_ready_for_formula_understanding is False
    assert "m2_ready: false" in markdown
    assert "m2_ready_for_formula_understanding: false" in markdown
    assert "```text" in markdown
    assert "```latex" not in markdown


def test_visual_audit_report_contains_public_metrics(tmp_path) -> None:
    from researchsensei.canonical.quality_gate import M1QualityGate
    from researchsensei.canonical.visual_audit import M1VisualAuditReportGenerator

    blocks = [_block("b001", page=3, block_type="formula", latex="x=y", section="Method")]
    quality = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    report = M1VisualAuditReportGenerator().write(
        output_dir=tmp_path,
        paper_id="p-test",
        title="A Test Paper",
        blocks=blocks,
        quality=quality,
        metrics={"runtime_seconds": 1.2, "ollama_json_valid": 0, "ollama_json_invalid": 1},
    )

    html = Path(report.html_path).read_text(encoding="utf-8")
    public = Path(report.public_report_path).read_text(encoding="utf-8")
    assert "formula_count" in html
    assert "ollama_json_invalid" in public
    assert "high_risk_count" in public
    assert "m2_ready_for_formula_understanding" in public


def test_m1_v2_pipeline_orchestrates_refine_gate_build_and_reports(tmp_path) -> None:
    from researchsensei.canonical.pipeline_v2 import M1V2CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study robust anomaly detection."),
        _block("b003", page=3, block_type="title", text="3 Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)"),
    ]

    result = M1V2CanonicalPipeline().run_from_blocks(
        paper_id="p-pipeline",
        title="Pipeline Paper",
        blocks=blocks,
        output_dir=tmp_path,
        formula_slots=_reviewed_slots(blocks),
    )

    assert result.canonicalization.m2_ready is True
    assert result.quality.status == CanonicalQualityStatus.PASS
    assert Path(result.canonicalization.canonical_paper_path).exists()
    assert Path(result.report.html_path).exists()
    assert result.metrics["primary_parser"] == "mineru25pro"
    assert result.metrics["ollama_enabled"] is False


def test_m1_v2_pipeline_default_formula_slots_require_crop_overlay(tmp_path) -> None:
    from researchsensei.canonical.pipeline_v2 import M1V2CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study robust anomaly detection."),
        _block("b003", page=3, block_type="title", text="3 Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)"),
    ]

    result = M1V2CanonicalPipeline().run_from_blocks(
        paper_id="p-missing-review",
        title="Missing Review Pipeline Paper",
        blocks=blocks,
        output_dir=tmp_path,
    )

    assert result.quality.status == CanonicalQualityStatus.FAIL
    assert result.quality.missing_crop_count == 1
    assert result.quality.missing_overlay_count == 1
    assert result.canonicalization.m2_ready is False


def test_m1_v2_pipeline_run_pdf_unpacks_mineru_payload_and_records_stats(tmp_path) -> None:
    from researchsensei.canonical.pipeline_v2 import M1V2CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="Readable abstract text.", section="Abstract"),
    ]

    class FakeMinerUAdapter:
        def parse_pdf(self, pdf_path, *, output_dir=None):
            return blocks, {
                "stats": {
                    "parser": "mineru25pro",
                    "pages": 2,
                    "total_blocks": len(blocks),
                    "elapsed_seconds": 0.25,
                },
                "pages": [{"page": 1, "blocks": []}, {"page": 2, "blocks": []}],
            }

    result = M1V2CanonicalPipeline(mineru_adapter=FakeMinerUAdapter()).run_pdf(
        paper_id="p-run-pdf",
        title="Run PDF Paper",
        pdf_path=tmp_path / "source.pdf",
        output_dir=tmp_path,
    )

    assert [block.block_id for block in result.blocks] == ["b001", "b002"]
    assert result.metrics["mineru_raw_payload_parser"] == "mineru25pro"
    assert result.metrics["mineru_raw_payload_pages"] == 2
    assert result.metrics["mineru_raw_payload_total_blocks"] == len(blocks)
    assert result.report.metrics["mineru_raw_payload_total_blocks"] == len(blocks)


def test_m1_v2_pipeline_keeps_failed_gate_out_of_m2(tmp_path) -> None:
    from researchsensei.canonical.pipeline_v2 import M1V2CanonicalPipeline

    blocks = [
        _block(f"b{i:03d}", page=i + 3, block_type="formula", latex=f"x_{i}=y", section="Abstract")
        for i in range(6)
    ]

    result = M1V2CanonicalPipeline().run_from_blocks(
        paper_id="p-fail",
        title="Failed Pipeline Paper",
        blocks=blocks,
        output_dir=tmp_path,
        apply_rule_refiner=False,
    )

    markdown = Path(result.canonicalization.canonical_paper_path).read_text(encoding="utf-8")
    assert result.canonicalization.m2_ready is False
    assert result.quality.status == CanonicalQualityStatus.FAIL
    assert "m2_ready: false" in markdown
