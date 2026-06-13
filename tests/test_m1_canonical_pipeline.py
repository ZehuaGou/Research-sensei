from __future__ import annotations

import inspect
import json
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
        reading_order=int("".join(c for c in block_id if c.isdigit()) or 0),
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


def _make_test_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((24, 35), "3 Method", fontsize=12)
    page.insert_text((24, 60), "x_t = f(h_t)", fontsize=12)
    doc.save(path)
    doc.close()


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


def test_mineru25_adapter_normalizes_official_content_block_shape() -> None:
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter()
    blocks = adapter.normalize_page_result(
        [
            {
                "type": "equation_block",
                "bbox": [0.10, 0.20, 0.80, 0.30],
                "angle": None,
                "content": "\\[x_t = f(h_t)\\]",
            },
            {
                "type": "ref_text",
                "bbox": [0.10, 0.70, 0.80, 0.80],
                "content": "[1] A reference.",
            },
        ],
        page=2,
    )

    assert [b.block_type for b in blocks] == ["formula", "reference"]
    assert blocks[0].bbox == [0.10, 0.20, 0.80, 0.30]
    assert blocks[0].latex == "x_t = f(h_t)"
    assert blocks[0].text == ""


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


def test_rule_based_refiner_treats_hyphenated_model_heading_as_method() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=1, block_type="title", text="1 Introduction"),
        _block("b002", page=3, block_type="title", text="2 Background"),
        _block("b003", page=5, block_type="title", text="4 Temporal Physics-informed Diffusion Model (TPIDM)"),
        _block("b004", page=5, block_type="formula", latex="L=L_{DM}+L_{PI}"),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert by_id["b003"].section == "Method"
    assert by_id["b004"].section == "Method"


def test_rule_based_refiner_infers_acronym_method_section() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=1, block_type="title", text="1 Introduction"),
        _block("b002", page=3, block_type="title", text="2 Related Work"),
        _block("b003", page=7, block_type="title", text="3. CARLA"),
        _block("b004", page=7, text="CARLA has two training stages."),
        _block("b005", page=11, block_type="formula", latex="L=L_{pre}+L_{self}"),
        _block("b006", page=16, block_type="title", text="4. Experiments"),
        _block("b007", page=16, text="We evaluate CARLA on benchmarks."),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert by_id["b003"].section == "Method"
    assert by_id["b004"].section == "Method"
    assert by_id["b005"].section == "Method"
    assert by_id["b007"].section == "Experiments"


def test_rule_based_refiner_subsections_inherit_numbered_parent_section() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=16, block_type="title", text="4. Experiments"),
        _block("b002", page=16, block_type="title", text="4.1. Benchmark Datasets"),
        _block("b003", page=17, text="Dataset details."),
        _block("b004", page=18, block_type="title", text="4.2. Benchmark Methods"),
        _block("b005", page=18, text="Baselines are compared with the proposed model."),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert by_id["b002"].section == "Experiments"
    assert by_id["b004"].section == "Experiments"
    assert by_id["b005"].section == "Experiments"


def test_rule_based_refiner_marks_bare_page_number_footer() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=15, block_type="title", text="3 Method"),
        _block("b002", page=15, text="15", bbox=[0.49, 0.936, 0.51, 0.95]),
        _block("b003", page=15, text="15 classes are used.", bbox=[0.10, 0.30, 0.80, 0.34]),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert "PAGE_NUMBER_FOOTER" in by_id["b002"].risk_flags
    assert "PAGE_NUMBER_FOOTER" not in by_id["b003"].risk_flags


def test_rule_based_refiner_uses_reading_order_not_final_page_heading() -> None:
    from researchsensei.canonical.structure_refiner import RuleBasedStructureRefiner

    blocks = [
        _block("b001", page=8, block_type="title", text="5 Experiments"),
        _block("b002", page=10, block_type="title", text="5.2.1 Ablations"),
        _block("b003", page=10, block_type="formula", latex="F_1=2PR/(P+R)"),
        _block("b004", page=10, block_type="title", text="6 Conclusion"),
        _block("b005", page=10, text="We conclude the paper."),
    ]

    refined = RuleBasedStructureRefiner().refine(blocks)

    by_id = {b.block_id: b for b in refined}
    assert by_id["b003"].section == "Experiments"
    assert by_id["b005"].section == "Conclusion"


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


def test_ollama_client_retries_invalid_json_once(monkeypatch) -> None:
    from researchsensei.canonical.ollama_refiner import OllamaStructuredClient

    calls = {"count": 0}

    class FakeResponse:
        status_code = 200

        def __init__(self, content: str) -> None:
            self.content = content

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"message": {"content": self.content}}

    def fake_post(url, json, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse("not-json")
        return FakeResponse('{"assignments": []}')

    monkeypatch.setattr("httpx.post", fake_post)

    client = OllamaStructuredClient(model="qwen2.5:0.5b", timeout_seconds=3, max_retries=1)
    payload = client.chat_json("assign sections", schema={"type": "object"})

    assert payload == {"assignments": []}
    assert calls["count"] == 2
    assert client.retry_count == 1
    assert client.json_invalid_count == 1
    assert client.json_valid_count == 1


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


def test_pipeline_can_enable_ollama_latex_without_section_refiner(tmp_path) -> None:
    from researchsensei.canonical.ollama_latex_validator import LatexValidationMetrics
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    blocks = [
        _block("b001", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b002", page=3, block_type="formula", latex=r"\mathcal {L} = x", section="Method"),
    ]
    slots = _reviewed_slots(blocks)

    class RaisingRefiner:
        metrics = type("Metrics", (), {
            "json_valid_count": 0,
            "json_invalid_count": 0,
            "retry_count": 0,
            "timeout_count": 0,
            "changed_by_count": 0,
        })()

        def refine(self, blocks):
            raise AssertionError("section refiner should not run for formula-only Ollama")

    class FakeLatexValidator:
        metrics = LatexValidationMetrics(
            available=True,
            model="fake-vision",
            formulas_checked=1,
            formulas_corrected=1,
            json_valid_count=1,
        )

        def is_available(self):
            return True

        def validate_formulas(self, formula_slots, output_dir):
            updated = []
            for slot in formula_slots:
                copy = dict(slot)
                copy.setdefault("final_latex_raw", copy["final_latex"])
                copy["final_latex"] = r"\mathcal{L} = x"
                copy["latex_corrected_by"] = "ollama_latex_validator"
                copy["latex_correction_confidence"] = 0.97
                updated.append(copy)
            return updated

    result = M1CanonicalPipeline(
        ollama_refiner=RaisingRefiner(),
        latex_validator=FakeLatexValidator(),
    ).run_from_blocks(
        paper_id="p-ollama-latex",
        title="Ollama Latex Paper",
        blocks=blocks,
        output_dir=tmp_path,
        apply_ollama=False,
        apply_ollama_latex=True,
        formula_slots=slots,
    )

    canonical = Path(result.canonicalization.canonical_paper_path).read_text(encoding="utf-8")
    persisted_slots = json.loads((tmp_path / "formula_slots.json").read_text(encoding="utf-8"))
    assert result.metrics["ollama_enabled"] is False
    assert result.metrics["ollama_latex_requested"] is True
    assert result.metrics["ollama_latex_enabled"] is True
    assert result.metrics["latex_validated"] is True
    assert result.metrics["latex_validator_corrected"] == 1
    assert result.metrics["latex_validator_overexpanded"] == 0
    assert result.metrics["latex_validator_anchor_mismatch"] == 0
    assert result.metrics["latex_validator_tag_restored"] == 0
    assert result.blocks[1].latex == r"\mathcal{L} = x"
    assert r"\mathcal{L} = x" in canonical
    assert persisted_slots[0]["final_latex"] == r"\mathcal{L} = x"
    assert persisted_slots[0]["final_latex_raw"] == r"\mathcal {L} = x"
    assert persisted_slots[0]["latex_corrected_by"] == "ollama_latex_validator"


def test_ollama_latex_validator_rejects_relation_operand_swap(tmp_path) -> None:
    from researchsensei.canonical.ollama_latex_validator import (
        LatexValidationResult,
        OllamaLatexValidator,
    )

    crop_path = tmp_path / "formula.png"
    crop_path.write_bytes(b"not-used-by-test")
    original = (
        r"\text{Anomaly label} (w_{t}): \left\{ \begin{array}{l l} "
        r"0, & \text{if} \forall c \in \mathcal{C}, "
        r"\phi_{s}^{C_{m}} (w_{t}) \geq \phi_{s}^{c} (w_{t}) \\ "
        r"1, & \text{otherwise} \end{array} \right. \tag{7}"
    )
    swapped = (
        r"\text{Anomaly label} \left(w_t\right):\begin{cases} "
        r"0, & \text{if } \forall c \in \mathcal{C}, "
        r"\phi^{c}_{s}(w_t) \geq \phi^{C_m}_{s}(w_t) \\ "
        r"1, & \text{otherwise} \end{cases} \tag{7}"
    )

    class SwappingValidator(OllamaLatexValidator):
        def is_available(self) -> bool:
            return True

        def _validate_single(self, formula_id, crop_path, current_latex):
            return LatexValidationResult(
                formula_id=formula_id,
                corrected_latex=swapped,
                confidence=0.95,
                issues_found=["swapped operands"],
            )

    validator = SwappingValidator()
    slots = [
        {
            "formula_id": "formula_008",
            "crop_path": crop_path.name,
            "final_latex": original,
            "risk_flags": [],
        }
    ]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == original
    assert "latex_corrected_by" not in updated[0]
    assert "OLLAMA_LATEX_RELATION_OPERAND_MISMATCH" in updated[0]["risk_flags"]
    assert validator.metrics.formulas_corrected == 0
    assert validator.metrics.anchor_mismatch_count == 1


def test_ollama_latex_validator_rejects_low_confidence_changes(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula.png"
    crop.write_bytes(b"fake-image")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": 123,
                        "corrected_latex": "x = z",
                        "confidence": 0.42,
                        "issues_found": ["uncertain"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_001",
        "crop_path": crop.name,
        "final_latex": "x = y",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == "x = y"
    assert "OLLAMA_LATEX_LOW_CONFIDENCE" in updated[0]["risk_flags"]
    assert validator.metrics.formulas_checked == 1
    assert validator.metrics.formulas_corrected == 0
    assert validator.metrics.low_confidence_count == 1
    assert validator.metrics.json_valid_count == 1


def test_ollama_latex_validator_prefers_group_crop_for_polish(tmp_path, monkeypatch) -> None:
    import base64

    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    single = tmp_path / "single.png"
    group = tmp_path / "group.png"
    single.write_bytes(b"single-crop")
    group.write_bytes(b"group-crop")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_001",
                        "corrected_latex": r"\mathbf{Q} = \mathbf{W}_{Q}H",
                        "confidence": 0.96,
                        "issues_found": ["spacing"],
                        "needs_human_check": False,
                    })
                }
            }

    def fake_post(url, json, timeout):
        captured["image_bytes"] = base64.b64decode(json["messages"][0]["images"][0])
        captured["think"] = json.get("think")
        captured["options_think"] = json.get("options", {}).get("think")
        captured["prompt"] = json["messages"][0]["content"]
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_001",
        "crop_path": single.name,
        "group_crop_path": group.name,
        "final_latex": r"\mathbf {Q} = \mathbf {W} _ {Q}H",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert captured["image_bytes"] == b"group-crop"
    assert captured["think"] is False
    assert captured["options_think"] is False
    assert "Return formula_id exactly as: formula_001" in captured["prompt"]
    assert updated[0]["final_latex"] == r"\mathbf{Q} = \mathbf{W}_{Q}H"
    assert updated[0]["final_latex_raw"] == r"\mathbf {Q} = \mathbf {W} _ {Q}H"
    assert updated[0]["latex_corrected_by"] == "ollama_latex_validator"
    assert validator.metrics.formulas_corrected == 1


def test_ollama_latex_validator_rejects_group_crop_overexpansion(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula_group.png"
    crop.write_bytes(b"group-crop")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_009",
                        "corrected_latex": (
                            r"$\mathbf{Q}=\mathbf{W}_{Q}H$" "\n"
                            r"$\mathbf{K}=\mathbf{W}_{K}H$" "\n"
                            r"$\mathbf{S}=\operatorname{softmax}(\mathbf{Q}\mathbf{K}^{T}/\sqrt{d_{h}})$"
                        ),
                        "confidence": 0.96,
                        "issues_found": ["expanded group"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_009",
        "group_crop_path": crop.name,
        "final_latex": r"\mathbf {S} = \operatorname{softmax}(\mathbf {Q}\mathbf {K}^{T}/\sqrt {d_{h}})",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == slots[0]["final_latex"]
    assert "OLLAMA_LATEX_OVEREXPANDED_GROUP" in updated[0]["risk_flags"]
    assert validator.metrics.formulas_corrected == 0
    assert validator.metrics.overexpanded_count == 1


def test_ollama_latex_validator_rejects_group_crop_lhs_mismatch(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula_group.png"
    crop.write_bytes(b"group-crop")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_009",
                        "corrected_latex": r"\mathbf {Q} = \mathbf {W}_{\mathbf {Q}} \cdot \mathbf {H}_{\mathrm{emb}}",
                        "confidence": 1.0,
                        "issues_found": ["returned first line of group"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_009",
        "group_crop_path": crop.name,
        "final_latex": r"\mathbf {S} = \operatorname{softmax}\left(\frac{\mathbf {Q}\cdot\mathbf {K}^{\top}}{\sqrt{d}}\right)",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == slots[0]["final_latex"]
    assert "OLLAMA_LATEX_LHS_MISMATCH" in updated[0]["risk_flags"]
    assert validator.metrics.formulas_corrected == 0
    assert validator.metrics.anchor_mismatch_count == 1


def test_ollama_latex_validator_strips_single_formula_math_wrappers(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula.png"
    crop.write_bytes(b"fake-image")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_001",
                        "corrected_latex": r"$x=y$",
                        "confidence": 0.99,
                        "issues_found": ["spacing"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_001",
        "crop_path": crop.name,
        "final_latex": r"x = y",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == r"x=y"
    assert updated[0]["latex_corrected_by"] == "ollama_latex_validator"
    assert validator.metrics.formulas_corrected == 1


def test_ollama_latex_validator_strips_trailing_single_line_break(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula.png"
    crop.write_bytes(b"fake-image")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_018",
                        "corrected_latex": r"\mathbf {Y}_{\mathrm{sta}}^{S} = \text { shuffle }(\mathbf {Y}_{\mathrm{sta}}) \\",
                        "confidence": 0.93,
                        "issues_found": ["line break"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_018",
        "crop_path": crop.name,
        "final_latex": r"\mathbf {Y}_{\mathrm{sta}}^{S} = \text { shuffle }(\mathbf {Y}_{\mathrm{sta}})",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == r"\mathbf{Y}_{\mathrm{sta}}^{S} = \text{shuffle}(\mathbf{Y}_{\mathrm{sta}})"
    assert updated[0]["latex_corrected_by"] == "ollama_latex_validator"
    assert validator.metrics.formulas_corrected == 1


def test_ollama_latex_validator_removes_duplicate_parenthetical_tag(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula.png"
    crop.write_bytes(b"fake-image")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_017",
                        "corrected_latex": r"$x=y$ (17)",
                        "confidence": 0.99,
                        "issues_found": ["spacing"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_017",
        "crop_path": crop.name,
        "final_latex": r"x = y \tag {17}",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == r"x=y \tag {17}"
    assert updated[0]["latex_tag_restored"] is True
    assert updated[0]["latex_corrected_by"] == "ollama_latex_validator"
    assert validator.metrics.formulas_corrected == 1


def test_ollama_latex_validator_restores_dropped_tag_before_applying(tmp_path, monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    crop = tmp_path / "formula.png"
    crop.write_bytes(b"fake-image")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "formula_id": "formula_001",
                        "corrected_latex": r"x=y",
                        "confidence": 0.99,
                        "issues_found": ["removed tag"],
                        "needs_human_check": False,
                    })
                }
            }

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    validator = OllamaLatexValidator(min_confidence=0.8)
    validator.is_available = lambda: True
    slots = [{
        "formula_id": "formula_001",
        "crop_path": crop.name,
        "final_latex": r"x = y \tag {4}",
        "risk_flags": [],
    }]

    updated = validator.validate_formulas(slots, tmp_path)

    assert updated[0]["final_latex"] == r"x=y \tag {4}"
    assert updated[0]["latex_tag_restored"] is True
    assert updated[0]["latex_corrected_by"] == "ollama_latex_validator"
    assert "OLLAMA_LATEX_DROPPED_TAG" not in updated[0]["risk_flags"]
    assert validator.metrics.formulas_corrected == 1


def test_ollama_latex_validator_requires_configured_vision_model(monkeypatch) -> None:
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "models": [
                    {
                        "name": "qwen2.5:0.5b",
                        "model": "qwen2.5:0.5b",
                        "capabilities": ["completion"],
                    }
                ]
            }

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: FakeResponse())

    missing = OllamaLatexValidator(model="missing-vision")
    non_vision = OllamaLatexValidator(model="qwen2.5:0.5b")

    assert missing.is_available() is False
    assert "ollama_model_unavailable: missing-vision" in missing.metrics.warnings
    assert non_vision.is_available() is False
    assert "ollama_model_not_vision: qwen2.5:0.5b" in non_vision.metrics.warnings


def test_canonical_builder_preserves_formula_identity_and_gate_status(tmp_path) -> None:
    from researchsensei.canonical.canonical_builder import CanonicalBuilder
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract", section="Abstract"),
        _block("b002", page=1, text="We study anomaly detection.", section="Abstract"),
        _block("b003", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
    ]
    gate = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    result = CanonicalBuilder().build(
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
    from researchsensei.canonical.canonical_builder import CanonicalBuilder
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block(f"b{i:03d}", page=4, block_type="formula", text=f"raw-only formula {i}: score_t=max e_t", section="Method")
        for i in range(1, 6)
    ]
    quality = M1QualityGate().evaluate(blocks, formula_slots=_reviewed_slots(blocks))

    result = CanonicalBuilder().build(
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


def test_m1_pipeline_orchestrates_refine_gate_build_and_reports(tmp_path) -> None:
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study robust anomaly detection."),
        _block("b003", page=3, block_type="title", text="3 Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)"),
    ]

    result = M1CanonicalPipeline().run_from_blocks(
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


def test_m1_pipeline_default_formula_slots_require_crop_overlay(tmp_path) -> None:
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study robust anomaly detection."),
        _block("b003", page=3, block_type="title", text="3 Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)"),
    ]

    result = M1CanonicalPipeline().run_from_blocks(
        paper_id="p-missing-review",
        title="Missing Review Pipeline Paper",
        blocks=blocks,
        output_dir=tmp_path,
    )

    assert result.quality.status == CanonicalQualityStatus.FAIL
    assert result.quality.missing_crop_count == 1
    assert result.quality.missing_overlay_count == 1
    assert result.canonicalization.m2_ready is False


def test_m1_pipeline_generates_crop_overlay_for_pdf_backed_formula_slots(tmp_path) -> None:
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    pdf_path = tmp_path / "source.pdf"
    _make_test_pdf(pdf_path)
    blocks = [
        _block("b001", page=1, block_type="title", text="3 Method", bbox=[0.10, 0.10, 0.50, 0.15]),
        _block("b002", page=1, block_type="formula", latex="x_t=f(h_t)", bbox=[0.10, 0.25, 0.60, 0.38]),
    ]

    result = M1CanonicalPipeline().run_from_blocks(
        paper_id="p-reviewed",
        title="Reviewed Pipeline Paper",
        blocks=blocks,
        output_dir=tmp_path,
        source_pdf_path=str(pdf_path),
    )

    slots = json.loads((tmp_path / "formula_slots.json").read_text(encoding="utf-8"))
    canonical = Path(result.canonicalization.canonical_paper_path).read_text(encoding="utf-8")
    assert result.quality.status == CanonicalQualityStatus.PASS
    assert result.metrics["formula_crop_count"] == 1
    assert result.metrics["formula_overlay_count"] == 1
    assert 'source_pdf_path: "source.pdf"' in canonical
    assert str(tmp_path) not in canonical
    assert slots[0]["crop_path"].startswith("formula_crops/")
    assert slots[0]["overlay_path"].startswith("formula_overlays/")
    assert (tmp_path / slots[0]["crop_path"]).exists()
    assert (tmp_path / slots[0]["overlay_path"]).exists()


def test_m1_pipeline_run_pdf_unpacks_mineru_payload_and_records_stats(tmp_path) -> None:
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

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

    result = M1CanonicalPipeline(mineru_adapter=FakeMinerUAdapter()).run_pdf(
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
    raw_path = tmp_path / "raw_mineru_output.json"
    assert raw_path.exists()
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw["stats"]["parser"] == "mineru25pro"


def test_m1_pipeline_keeps_failed_gate_out_of_m2(tmp_path) -> None:
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    blocks = [
        _block(f"b{i:03d}", page=i + 3, block_type="formula", latex=f"x_{i}=y", section="Abstract")
        for i in range(6)
    ]

    result = M1CanonicalPipeline().run_from_blocks(
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


def test_slots_from_blocks_includes_m2_contract_fields(tmp_path) -> None:
    """Pipeline _slots_from_blocks must include all M2 contract fields."""
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study anomaly detection.", section="Abstract"),
        _block("b003", page=3, block_type="title", text="3 Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
        _block("b005", page=3, block_type="formula", latex="\\tag{2} y_t=g(x_t)", section="Method"),
    ]

    pipeline = M1CanonicalPipeline()
    slots = pipeline._slots_from_blocks(blocks)

    contract_fields = [
        "equation_number", "equation_group_id", "group_order",
        "group_crop_path", "nearby_text_before", "nearby_text_after",
        "section", "block_source", "final_origin", "risk_flags",
    ]
    for field in contract_fields:
        assert field in slots[0], f"Missing M2 contract field: {field}"
    assert slots[0]["section"] == "Method"
    assert slots[1]["equation_number"] == "2"
    assert slots[0]["equation_group_id"] != ""  # should be grouped


def test_builder_formula_slots_include_contract_fields() -> None:
    """CanonicalBuilder._formula_slots must produce M2 contract fields."""
    from researchsensei.canonical.canonical_builder import CanonicalBuilder

    blocks = [
        _block("b001", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b002", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
        _block("b003", page=3, block_type="formula", latex="\\tag{2} y_t=g(x_t)", section="Method"),
        _block("b004", page=5, block_type="formula", latex="L=E[\\log p(x)]", section="Method"),
    ]

    builder = CanonicalBuilder()
    slots = builder._formula_slots(blocks)

    assert len(slots) == 3
    for slot in slots:
        assert "equation_number" in slot
        assert "equation_group_id" in slot
        assert "group_order" in slot
        assert "group_crop_path" in slot
        assert "nearby_text_before" in slot
        assert "nearby_text_after" in slot
    assert slots[1]["equation_number"] == "2"


def test_page_header_footer_blocks_suppressed_from_canonical(tmp_path) -> None:
    """Repeated page header titles and footer lines must not appear in canonical markdown."""
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    # Simulate a paper with "EdgeConvFormer" as title on multiple pages
    blocks = [_block("b000", page=0, block_type="title", text="EdgeConvFormer Paper")]
    for i in range(1, 33):
        page = i
        blocks.append(_block(f"h{i:03d}", page=page, block_type="title", text="EdgeConvFormer"))
        blocks.append(_block(f"t{i:03d}", page=page, text=f"Content on page {i}."))
        blocks.append(_block(f"f{i:03d}", page=page, text=f"Page {i} of 32"))
        blocks.append(_block(f"a{i:03d}", page=page, text="Jie Liu et al.: Preprint submitted to Elsevier"))
    blocks.append(_block("b100", page=5, block_type="formula", latex="x_t=f(h_t)"))

    result = M1CanonicalPipeline().run_from_blocks(
        paper_id="p-header-test",
        title="Header Test Paper",
        blocks=blocks,
        output_dir=tmp_path,
    )
    markdown = Path(result.canonicalization.canonical_paper_path).read_text(encoding="utf-8")

    # Page header "EdgeConvFormer" should not appear as ### headings
    header_count = len([line for line in markdown.splitlines() if line.strip() == "### EdgeConvFormer"])
    assert header_count == 0, f"Found {header_count} page-header headings in canonical"

    # Footer "Page N of M" should not appear
    assert "Page 1 of 32" not in markdown
    assert "Page 32 of 32" not in markdown

    # Author footer should not appear
    assert "Preprint submitted to Elsevier" not in markdown


def test_quality_gate_raw_only_formula_dense_blocks_m2_formula_understanding() -> None:
    """When formula_count >= 5 and latex_count == 0, must be DEGRADED, not PASS."""
    from researchsensei.canonical.quality_gate import M1QualityGate

    blocks = [
        _block(f"b{i:03d}", page=1, block_type="formula", text=f"raw formula {i}")
        for i in range(8)
    ]

    gate = M1QualityGate()
    result = gate.evaluate(blocks, [])

    assert result.raw_only_formula_dense is True
    assert result.m2_ready_for_formula_understanding is False
    assert result.status == CanonicalQualityStatus.DEGRADED or result.status == CanonicalQualityStatus.FAIL
    assert "RAW_ONLY_FORMULA_DENSE_NO_LATEX" in result.warning_reasons
