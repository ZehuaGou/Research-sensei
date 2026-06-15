from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _write_m1_bundle(root: Path, *, formula_ready: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "visual_audit").mkdir()
    for folder in ["formula_crops", "formula_overlays", "formula_group_crops"]:
        (root / folder).mkdir()
    for path in [
        root / "formula_crops" / "formula_001_p3.png",
        root / "formula_crops" / "formula_002_p3.png",
        root / "formula_overlays" / "formula_001_page_3.png",
        root / "formula_overlays" / "formula_002_page_3.png",
        root / "formula_group_crops" / "eq_method_attention_p3.png",
    ]:
        path.write_bytes(b"png")
    (root / "canonical_paper.md").write_text(
        "\n".join(
            [
                "---",
                "paper_id: demo_paper",
                'title: "Demo Time Series Paper"',
                "canonical_quality_status: PASS",
                "m2_ready: true",
                f"m2_ready_for_formula_understanding: {'true' if formula_ready else 'false'}",
                "primary_parser: mineru25pro",
                "formula_slot_count: 2",
                "---",
                "",
                "# Demo Time Series Paper",
                "",
                "## Method",
                "",
                "We use an attention block and optimize a reconstruction loss.",
                "",
                "<!-- formula_id: formula_001 | origin: mineru_latex | section: Method | page: 3 | bbox: [0.1, 0.2, 0.3, 0.25] | source: mineru25pro | block_id: b_f1 -->",
                "```latex",
                r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d})V",
                "```",
                "",
                "<!-- formula_id: formula_002 | origin: mineru_latex | section: Method | page: 3 | bbox: [0.1, 0.26, 0.3, 0.3] | source: mineru25pro | block_id: b_f2 -->",
                "```latex",
                r"\mathcal{L}=\lVert X-\hat{X}\rVert_2^2",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    (root / "document_blocks.json").write_text(
        json.dumps(
            [
                {
                    "block_id": "b_title",
                    "page": 1,
                    "bbox": [0.1, 0.05, 0.8, 0.09],
                    "block_type": "title",
                    "text": "Demo Time Series Paper",
                    "latex": "",
                    "html": "",
                    "reading_order": 0,
                    "source": "mineru25pro",
                    "confidence": 0.95,
                    "parent_section": "",
                    "raw_payload_ref": "page_001.json",
                    "section": "Unknown",
                    "section_confidence": "low",
                    "section_reason": "front_matter",
                    "risk_flags": [],
                },
                {
                    "block_id": "b_front",
                    "page": 1,
                    "bbox": [0.1, 0.1, 0.8, 0.13],
                    "block_type": "text",
                    "text": "Author A is with the School of Computer Science, Example University. (E-mail: a@example.edu)",
                    "latex": "",
                    "html": "",
                    "reading_order": 1,
                    "source": "mineru25pro",
                    "confidence": 0.95,
                    "parent_section": "",
                    "raw_payload_ref": "page_001.json",
                    "section": "Introduction",
                    "section_confidence": "medium",
                    "section_reason": "reading_order_context",
                    "risk_flags": ["FRONT_MATTER_AFFILIATION"],
                },
                {
                    "block_id": "b_intro",
                    "page": 1,
                    "bbox": [0.1, 0.14, 0.8, 0.20],
                    "block_type": "text",
                    "text": "This paper studies robust time series anomaly detection from scarce normal data.",
                    "latex": "",
                    "html": "",
                    "reading_order": 2,
                    "source": "mineru25pro",
                    "confidence": 0.95,
                    "parent_section": "",
                    "raw_payload_ref": "page_001.json",
                    "section": "Introduction",
                    "section_confidence": "medium",
                    "section_reason": "reading_order_context",
                    "risk_flags": [],
                },
                {
                    "block_id": "b_page",
                    "page": 3,
                    "bbox": [0.91, 0.03, 0.93, 0.04],
                    "block_type": "text",
                    "text": "3",
                    "latex": "",
                    "html": "",
                    "reading_order": 0,
                    "source": "mineru25pro",
                    "confidence": 0.95,
                    "parent_section": "",
                    "raw_payload_ref": "page_003.json",
                    "section": "Unknown",
                    "section_confidence": "low",
                    "section_reason": "reading_order_context",
                    "risk_flags": ["PAGE_NUMBER_FOOTER"],
                },
                {
                    "block_id": "b_text",
                    "page": 3,
                    "bbox": [0.1, 0.1, 0.8, 0.18],
                    "block_type": "text",
                    "text": "We use an attention block and optimize a reconstruction loss.",
                    "latex": "",
                    "html": "",
                    "reading_order": 1,
                    "source": "mineru25pro",
                    "confidence": 0.95,
                    "parent_section": "",
                    "raw_payload_ref": "page_003.json",
                    "section": "Method",
                    "section_confidence": "high",
                    "section_reason": "heading",
                    "risk_flags": [],
                },
                {
                    "block_id": "b_f1",
                    "page": 3,
                    "bbox": [0.1, 0.2, 0.3, 0.25],
                    "block_type": "formula",
                    "text": "",
                    "latex": r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d})V",
                    "html": "",
                    "reading_order": 2,
                    "source": "mineru25pro",
                    "confidence": 0.92,
                    "parent_section": "",
                    "raw_payload_ref": "page_003.json",
                    "section": "Method",
                    "section_confidence": "high",
                    "section_reason": "heading",
                    "risk_flags": [],
                },
                {
                    "block_id": "b_f2",
                    "page": 3,
                    "bbox": [0.1, 0.26, 0.3, 0.3],
                    "block_type": "formula",
                    "text": "",
                    "latex": r"\mathcal{L}=\lVert X-\hat{X}\rVert_2^2",
                    "html": "",
                    "reading_order": 3,
                    "source": "mineru25pro",
                    "confidence": 0.88,
                    "parent_section": "",
                    "raw_payload_ref": "page_003.json",
                    "section": "Method",
                    "section_confidence": "high",
                    "section_reason": "heading",
                    "risk_flags": ["group_crop_contamination"],
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    slots = [
        {
            "formula_id": "formula_001",
            "block_id": "b_f1",
            "page": 3,
            "section": "Method",
            "final_latex": r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d})V",
            "equation_number": 6,
            "equation_group_id": "eq_method_attention",
            "group_order": 1,
            "group_crop_path": "formula_group_crops/eq_method_attention_p3.png",
            "nearby_text_before": "We use an attention block.",
            "nearby_text_after": "Then the loss is optimized.",
            "m2_ready": formula_ready,
            "risk_flags": [],
            "final_origin": "mineru_latex",
            "block_source": "mineru25pro",
            "bbox": [0.1, 0.2, 0.3, 0.25],
            "crop_path": "formula_crops/formula_001_p3.png",
            "overlay_path": "formula_overlays/formula_001_page_3.png",
            "nearby_block_ids": ["b_text"],
        },
        {
            "formula_id": "formula_002",
            "block_id": "b_f2",
            "page": 3,
            "section": "Method",
            "final_latex": r"\mathcal{L}=\lVert X-\hat{X}\rVert_2^2",
            "equation_number": 7,
            "equation_group_id": "",
            "group_order": 0,
            "group_crop_path": "",
            "nearby_text_before": "Then the loss is optimized.",
            "nearby_text_after": "",
            "m2_ready": formula_ready,
            "risk_flags": ["group_crop_contamination"],
            "final_origin": "mineru_latex",
            "block_source": "mineru25pro",
            "bbox": [0.1, 0.26, 0.3, 0.3],
            "crop_path": "formula_crops/formula_002_p3.png",
            "overlay_path": "formula_overlays/formula_002_page_3.png",
            "nearby_block_ids": ["b_text"],
        },
    ]
    (root / "formula_slots.json").write_text(json.dumps(slots, indent=2), encoding="utf-8")
    (root / "formula_slots.md").write_text("# Formula Slots\n", encoding="utf-8")
    (root / "paper_metadata.json").write_text(
        json.dumps({"paper_id": "demo_paper", "title": "Demo Time Series Paper", "authors": ["A"]}),
        encoding="utf-8",
    )
    (root / "quality_report.md").write_text(
        "# Quality\nMachine quality gate: PASS\nPerformance gate: WARNING\n",
        encoding="utf-8",
    )
    (root / "performance_report.json").write_text(
        json.dumps({"seconds_per_page": 178.9, "perf_pass": False, "warnings": ["seconds_per_page=179 > 120s threshold"]}),
        encoding="utf-8",
    )
    return root


def _hash_inputs(input_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in [
        "canonical_paper.md",
        "document_blocks.json",
        "formula_slots.json",
        "formula_slots.md",
        "paper_metadata.json",
        "quality_report.md",
        "performance_report.json",
    ]:
        data = (input_dir / name).read_bytes()
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def test_m2_runner_writes_required_outputs_and_does_not_modify_m1_inputs(tmp_path: Path) -> None:
    from researchsensei.m2.runner import run_m2_understanding

    input_dir = _write_m1_bundle(tmp_path / "m1")
    before = _hash_inputs(input_dir)
    output_dir = tmp_path / "m2"

    result = run_m2_understanding(input_dir=input_dir, output_dir=output_dir)

    assert result.run_summary["input_contract"]["status"] == "PASS"
    assert result.run_summary["m1_artifacts_modified"] is False
    assert _hash_inputs(input_dir) == before
    for name in [
        "m2_paper_understanding.md",
        "m2_formula_understanding.json",
        "m2_formula_understanding.md",
        "m2_method_graph.json",
        "m2_source_trace.json",
        "m2_risk_report.md",
        "m2_run_summary.json",
    ]:
        assert (output_dir / name).exists(), name


def test_m2_paper_understanding_skips_m1_front_matter_and_layout_risks(tmp_path: Path) -> None:
    from researchsensei.m2.runner import run_m2_understanding

    input_dir = _write_m1_bundle(tmp_path / "m1")
    output_dir = tmp_path / "m2"

    run_m2_understanding(input_dir=input_dir, output_dir=output_dir)

    paper = (output_dir / "m2_paper_understanding.md").read_text(encoding="utf-8")
    graph = json.loads((output_dir / "m2_method_graph.json").read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in graph["nodes"]}

    assert "scarce normal data" in paper
    assert "E-mail" not in paper
    assert "section:Unknown" not in node_ids


def test_m2_formula_understanding_uses_group_context_and_source_trace(tmp_path: Path) -> None:
    from researchsensei.m2.runner import run_m2_understanding

    input_dir = _write_m1_bundle(tmp_path / "m1")
    output_dir = tmp_path / "m2"

    run_m2_understanding(input_dir=input_dir, output_dir=output_dir)

    data = json.loads((output_dir / "m2_formula_understanding.json").read_text(encoding="utf-8"))
    first = data["formulas"][0]
    assert first["formula_id"] == "formula_001"
    assert first["equation_group_id"] == "eq_method_attention"
    assert first["final_latex"] == r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d})V"
    assert "formula_001" in first["group_context_used"]
    assert "group_crop_path=formula_group_crops/eq_method_attention_p3.png" in first["group_context_used"]
    assert first["role_guess"] == "attention computation"
    assert first["source_trace"]["source_artifacts"] == ["formula_slots.json", "document_blocks.json", "canonical_paper.md"]
    assert first["source_trace"]["immutable_fields"]["page"] == 3
    assert first["source_trace"]["immutable_fields"]["block_source"] == "mineru25pro"


def test_m2_formula_schema_preserves_risks_and_lowers_confidence(tmp_path: Path) -> None:
    from researchsensei.m2.runner import run_m2_understanding

    input_dir = _write_m1_bundle(tmp_path / "m1")
    output_dir = tmp_path / "m2"

    run_m2_understanding(input_dir=input_dir, output_dir=output_dir)

    data = json.loads((output_dir / "m2_formula_understanding.json").read_text(encoding="utf-8"))
    risky = data["formulas"][1]
    assert risky["risk_flags"] == ["group_crop_contamination"]
    assert risky["confidence"] < data["formulas"][0]["confidence"]
    assert risky["source_trace"]["formula_id"] == "formula_002"


def test_m2_skips_deep_formula_explanation_when_m1_formula_not_ready(tmp_path: Path) -> None:
    from researchsensei.m2.runner import run_m2_understanding

    input_dir = _write_m1_bundle(tmp_path / "m1", formula_ready=False)
    output_dir = tmp_path / "m2"

    run_m2_understanding(input_dir=input_dir, output_dir=output_dir)

    data = json.loads((output_dir / "m2_formula_understanding.json").read_text(encoding="utf-8"))
    first = data["formulas"][0]
    assert first["role_guess"] == "unknown"
    assert first["plain_language_explanation"].startswith("Skipped:")
    assert first["confidence"] <= 0.2
    assert "M1_FORMULA_NOT_READY" in first["risk_flags"]


def test_m2_front_matter_parser_keeps_underscore_paper_id_as_string() -> None:
    from researchsensei.m2.artifact_reader import parse_front_matter

    front_matter = parse_front_matter("---\npaper_id: 2510_18998\nformula_slot_count: 26\n---\n")

    assert front_matter["paper_id"] == "2510_18998"
    assert front_matter["formula_slot_count"] == 26


def test_m2_full_pipeline_writes_required_artifact_chain_without_llm(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_m1_bundle(tmp_path / "m1")
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BASELINE_ONLY"
    assert result.status.allowed_for_user_display is False
    for name in [
        "source_status.json",
        "canonical_status.json",
        "parsed_document.json",
        "passage_index.json",
        "claim_evidence.json",
        "evidence_index.json",
        "paper_skeleton.json",
        "evidence_pack.json",
        "understanding_status.json",
        "quality_report.json",
        "m2_run_summary.json",
    ]:
        assert (output_dir / name).exists(), name

    parsed = json.loads((output_dir / "parsed_document.json").read_text(encoding="utf-8"))
    formula_blocks = [block for block in parsed["blocks"] if block["type"] == "formula"]
    assert formula_blocks
    assert formula_blocks[0]["formula_id"] == "formula_001"
    assert formula_blocks[0]["formula_origin"] == "mineru_latex"
    assert formula_blocks[0]["crop_path"].endswith(".png")
    assert formula_blocks[0]["equation_group_id"] == "eq_method_attention"
    assert formula_blocks[0]["group_crop_path"] == "formula_group_crops/eq_method_attention_p3.png"


def test_m2_full_pipeline_missing_canonical_input_writes_blocked_status(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = tmp_path / "missing_m1"
    input_dir.mkdir()
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BLOCKED_UNDERSTANDING"
    assert result.status.blocking_reason == "MISSING_CANONICAL_INPUT"
    assert result.status.allowed_for_user_display is False
    assert result.status.component_status["llm"] == "SKIPPED"
    assert result.status.checked_artifacts == ["source_status", "quality_report", "understanding_status"]
    assert (output_dir / "source_status.json").exists()
    assert (output_dir / "quality_report.json").exists()
    assert (output_dir / "understanding_status.json").exists()
    assert (output_dir / "m2_run_summary.json").exists()
    assert not (output_dir / "paper_card.json").exists()


def test_m2_full_pipeline_preflight_block_does_not_mark_llm_failed(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_m1_bundle(tmp_path / "m1")
    canonical = input_dir / "canonical_paper.md"
    canonical.write_text(
        canonical.read_text(encoding="utf-8").replace("m2_ready: true", "m2_ready: false"),
        encoding="utf-8",
    )
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BLOCKED_UNDERSTANDING"
    assert result.status.blocking_reason == "M1_M2_NOT_READY"
    assert result.status.component_status["paper_card"] == "SKIPPED"
    assert result.status.component_status["llm"] == "SKIPPED"
    assert not (output_dir / "paper_card.json").exists()


def test_m2_full_pipeline_blocks_when_no_passages(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_m1_bundle(tmp_path / "m1")
    (input_dir / "document_blocks.json").write_text("[]", encoding="utf-8")
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BLOCKED_UNDERSTANDING"
    assert result.status.blocking_reason == "NO_PASSAGES"
    assert result.status.allowed_for_user_display is False
    assert result.status.component_status["llm"] == "SKIPPED"
    status = json.loads((output_dir / "understanding_status.json").read_text(encoding="utf-8"))
    assert status["blocking_reason"] == "NO_PASSAGES"
    assert not (output_dir / "paper_card.json").exists()


def test_m2_full_pipeline_blocks_when_no_claims(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_m1_bundle(tmp_path / "m1")
    (input_dir / "document_blocks.json").write_text(
        json.dumps([
            {
                "block_id": "b_neutral",
                "page": 1,
                "bbox": [0.1, 0.1, 0.8, 0.2],
                "block_type": "text",
                "text": (
                    "Background material surveys temporal sensor streams across several deployments "
                    "and records descriptive observations about data collection practice."
                ),
                "latex": "",
                "html": "",
                "reading_order": 1,
                "source": "mineru25pro",
                "confidence": 0.95,
                "parent_section": "",
                "raw_payload_ref": "page_001.json",
                "section": "Related Work",
                "section_confidence": "high",
                "section_reason": "heading",
                "risk_flags": [],
            }
        ]),
        encoding="utf-8",
    )
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BLOCKED_UNDERSTANDING"
    assert result.status.blocking_reason == "NO_CLAIMS"
    assert result.status.component_status["evidence_pack"] == "SUCCESS"
    assert result.status.component_status["llm"] == "SKIPPED"
    assert not (output_dir / "paper_card.json").exists()


def test_m2_full_pipeline_blocks_llm_path_without_method_evidence(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    class ShouldNotCallLLM:
        async def chat_json(self, messages, *, config=None):
            raise AssertionError("LLM must not be called before METHOD evidence exists")

    input_dir = _write_m1_bundle(tmp_path / "m1")
    (input_dir / "document_blocks.json").write_text(
        json.dumps([
            {
                "block_id": "b_intro",
                "page": 1,
                "bbox": [0.1, 0.1, 0.8, 0.2],
                "block_type": "text",
                "text": (
                    "We propose a calibrated residual detector for temporal sensor windows and "
                    "summarize its intended anomaly detection setting."
                ),
                "latex": "",
                "html": "",
                "reading_order": 1,
                "source": "mineru25pro",
                "confidence": 0.95,
                "parent_section": "",
                "raw_payload_ref": "page_001.json",
                "section": "Introduction",
                "section_confidence": "high",
                "section_reason": "heading",
                "risk_flags": [],
            }
        ]),
        encoding="utf-8",
    )
    output_dir = tmp_path / "m2_full"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir, llm_client=ShouldNotCallLLM())

    assert result.status.status == "BLOCKED_UNDERSTANDING"
    assert result.status.blocking_reason == "MISSING_METHOD_EVIDENCE"
    assert result.status.component_status["llm"] == "SKIPPED"
    assert not (output_dir / "paper_card.json").exists()


class ScriptedM2LLMClient:
    def __init__(self) -> None:
        self.calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        text = "\n".join(message.content for message in messages)
        if "formula_cards" in text and "Formula evidence" in text:
            return {
                "formula_cards": [
                    {
                        "formula_id": "formula_001",
                        "formula_raw": r"\operatorname{Attention}(Q,K,V)=\operatorname{softmax}(QK^\top/\sqrt{d})V",
                        "formula_origin": "mineru_latex",
                        "formula_ocr_status": "not_required",
                        "formula_explanation_status": "parser_derived",
                        "purpose": "解释注意力块如何组合 Q/K/V。",
                        "intuition": "用 Q 和 K 计算权重，再加权 V。",
                        "numeric_example": "INSUFFICIENT_EVIDENCE",
                        "plain_summary": "该公式描述注意力计算。",
                        "evidence_ref": "demo_paper:b_f1",
                    }
                ]
            }
        if "teaching_cards" in text:
            return {
                "teaching_cards": [
                    {
                        "target_type": "concept",
                        "title": "Attention block",
                        "human_explanation": "该模块用注意力机制处理时间序列表示。",
                        "analogy_explanation": "像给不同输入片段分配重要性。",
                        "minimal_formula_explanation": "softmax(QK^T/sqrt(d))V",
                        "numeric_example": "INSUFFICIENT_EVIDENCE",
                        "paper_role_explanation": "它是方法部分的核心计算模块。",
                        "evidence_ref": "demo_paper:b_text",
                    }
                ]
            }
        return {
            "one_sentence_summary": "论文研究时间序列异常检测中的注意力和重构损失。",
            "problem": {"text": "论文研究时间序列异常检测问题。", "evidence_ref": "demo_paper:b_text"},
            "core_idea": {"text": "方法使用 attention block 并优化重构损失。", "evidence_ref": "demo_paper:b_text"},
            "method_overview": {"text": "方法部分描述 attention block 和 reconstruction loss。", "evidence_ref": "demo_paper:b_text"},
            "experiment_summary": {"text": "INSUFFICIENT_EVIDENCE", "evidence_ref": "demo_paper:b_text"},
            "limitations": {"text": "INSUFFICIENT_EVIDENCE", "evidence_ref": ""},
        }


def test_m2_full_pipeline_llm_path_preserves_formula_origin_and_passes_audit(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_m1_bundle(tmp_path / "m1")
    output_dir = tmp_path / "m2_full"
    client = ScriptedM2LLMClient()

    result = run_m2_full_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        llm_client=client,
        llm_metadata={"provider": "scripted", "model": "scripted"},
    )

    assert result.status.status == "SUCCESS"
    assert client.calls == 3
    assert result.run_summary["formula_evidence_pack_count"] == 2
    assert result.run_summary["formula_card_count"] == 2
    assert result.run_summary["formula_card_coverage"]["status"] == "PASS"
    status = json.loads((output_dir / "understanding_status.json").read_text(encoding="utf-8"))
    assert status["allowed_for_user_display"] is True
    formulas = json.loads((output_dir / "formula_cards.json").read_text(encoding="utf-8"))
    assert len(formulas["formula_cards"]) == 2
    by_id = {card["formula_id"]: card for card in formulas["formula_cards"]}
    first = by_id["formula_001"]
    assert first["formula_origin"] == "mineru_latex"
    assert first["formula_explanation_status"] == "parser_derived"
    assert first["evidence_ref"] == "demo_paper:b_f1"
    assert first["coverage_status"] == "LLM_EXPLAINED"
    assert first["equation_group_id"] == "eq_method_attention"
    second = by_id["formula_002"]
    assert second["evidence_ref"] == "demo_paper:b_f2"
    assert second["coverage_status"] == "SUMMARY_ONLY"
    assert second["derivation_status"] == "summary_only"
    assert "LLM_CARD_MISSING" in second["warnings"]
    quality = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
    assert not [finding for finding in quality["findings"] if finding["effect"] == "BLOCK"]


def test_m2_audit_warning_is_preserved_in_understanding_status() -> None:
    from researchsensei.m2.full_pipeline import _audit_candidate, _success_status
    from researchsensei.schemas import EvidencePackSummary, FormulaCardBundle

    evidence_text = (
        "Temporal graph anomaly detector uses calibrated residual attention over "
        "sensor windows with benchmark deployment constraints."
    )
    paper_card = {
        "paper_id": "test",
        "title": "Temporal Graph Residual Anomaly Detection",
        "one_sentence_summary": "The paper studies calibrated residual attention for sensor anomaly detection.",
        "problem": {"text": "Temporal graph anomaly detection on sensor windows.", "evidence_ref": "test:b001"},
        "core_idea": {"text": "Calibrated residual attention scores unusual sensor windows.", "evidence_ref": "test:b002"},
        "method_overview": {"text": "The method combines graph attention with residual calibration.", "evidence_ref": "test:b002"},
        "experiment_summary": {"text": "Benchmarks evaluate sensor-window anomaly detection.", "evidence_ref": "test:b003"},
        "limitations": {"text": evidence_text, "evidence_ref": "test:b004"},
    }
    card_artifacts = {
        "paper_card": paper_card,
        "formula_cards": FormulaCardBundle(paper_id="test", formula_cards=[]),
        "teaching_cards": {
            "paper_id": "test",
            "teaching_cards": [{
                "card_id": "t1",
                "human_explanation": "The detector scores unusual sensor windows.",
                "analogy_explanation": "It is like highlighting the most suspicious dashboard segments.",
                "evidence_refs": ["test:b002"],
            }],
        },
    }
    claim_evidence = {
        "schema_version": "v2",
        "paper_id": "test",
        "claims": [
            {
                "claim_id": "c1",
                "evidence_ref": "test:b001",
                "passage_id": "p1",
                "claim_type": "PROBLEM",
                "claim_text": "Temporal graph anomaly detection on sensor windows.",
                "quote_or_summary": "Temporal graph anomaly detection on sensor windows.",
                "canonical_source_path": "canonical_paper.md",
            },
            {
                "claim_id": "c2",
                "evidence_ref": "test:b002",
                "passage_id": "p2",
                "claim_type": "METHOD",
                "claim_text": "Calibrated residual attention scores unusual sensor windows.",
                "quote_or_summary": "Calibrated residual attention scores unusual sensor windows.",
                "canonical_source_path": "canonical_paper.md",
            },
            {
                "claim_id": "c3",
                "evidence_ref": "test:b003",
                "passage_id": "p3",
                "claim_type": "RESULT",
                "claim_text": "Benchmarks evaluate sensor-window anomaly detection.",
                "quote_or_summary": "Benchmarks evaluate sensor-window anomaly detection.",
                "canonical_source_path": "canonical_paper.md",
            },
            {
                "claim_id": "c4",
                "evidence_ref": "test:b004",
                "passage_id": "p4",
                "claim_type": "LIMITATION",
                "claim_text": evidence_text,
                "quote_or_summary": evidence_text,
                "canonical_source_path": "canonical_paper.md",
            },
        ],
    }
    passage_index = {
        "schema_version": "v2",
        "paper_id": "test",
        "passages": [
            {"passage_id": f"p{i}", "text": f"passage {i}", "section": "method"}
            for i in range(1, 5)
        ],
    }
    evidence_index = {
        "paper_id": "test",
        "claims": [
            {"claim_id": claim["claim_id"], "evidence_ref": claim["evidence_ref"], "quote_or_summary": claim["quote_or_summary"]}
            for claim in claim_evidence["claims"]
        ],
    }
    summary = EvidencePackSummary(
        included_claim_ids=["c1", "c2", "c3", "c4"],
        total_tokens=48,
        claim_type_counts={"PROBLEM": 1, "METHOD": 1, "RESULT": 1, "LIMITATION": 1},
    )
    status = _success_status("test", card_artifacts["formula_cards"], summary)

    quality_report, updated_status, updated_cards = _audit_candidate(
        paper_id="test",
        status=status,
        card_artifacts=card_artifacts,
        canonical_status={"paper_id": "test", "canonicalization_status": "success", "m2_ready": True},
        evidence_index=evidence_index,
        claim_evidence=claim_evidence,
        passage_index=passage_index,
        paper_skeleton={"paper_id": "test", "title": "Temporal Graph Residual Anomaly Detection"},
        survey_artifacts={
            "survey_status": {"status": "NOT_APPLICABLE"},
            "survey_landscape": {},
            "method_taxonomy": {},
            "extracted_key_papers": {},
            "survey_claims": {},
        },
    )

    assert updated_status.status == "SUCCESS"
    assert updated_cards == card_artifacts
    assert any(finding.code == "F-11" and finding.effect == "WARNING" for finding in quality_report.findings)
    assert any(warning.code == "F-11" for warning in updated_status.warnings)


def test_single_paper_v2_uses_all_formula_evidence_pack_for_formula_cards(tmp_path: Path) -> None:
    from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
    from researchsensei.jobs import JobStore
    from researchsensei.schemas import EvidencePack, EvidencePackItem, EvidencePackSummary, PaperSkeleton
    from researchsensei.workspace import WorkspaceStore

    class EmptyFormulaBatchLLM:
        def __init__(self) -> None:
            self.formula_prompt_refs: list[list[str]] = []

        async def chat_json(self, messages, *, config=None):
            text = "\n".join(message.content for message in messages)
            if "Formula evidence batch" in text:
                refs = [
                    line.split(":", 1)[1].strip()
                    for line in text.splitlines()
                    if line.strip().startswith("- evidence_ref:")
                ]
                self.formula_prompt_refs.append(refs)
                return {"formula_cards": []}
            if "teaching_cards" in text:
                return {
                    "teaching_cards": [{
                        "target_type": "concept",
                        "title": "Method evidence",
                        "human_explanation": "The method evidence explains the model design.",
                        "analogy_explanation": "It is like a compact recipe for the model.",
                        "minimal_formula_explanation": "INSUFFICIENT_EVIDENCE",
                        "numeric_example": "INSUFFICIENT_EVIDENCE",
                        "paper_role_explanation": "It grounds the M2 teaching card.",
                        "evidence_ref": "paper:b_method",
                    }]
                }
            return {
                "one_sentence_summary": "The paper proposes a formula-heavy method.",
                "problem": {"text": "The paper studies a method problem.", "evidence_ref": "paper:b_method"},
                "core_idea": {"text": "The method uses multiple equations.", "evidence_ref": "paper:b_method"},
                "method_overview": {"text": "The method is described by evidence.", "evidence_ref": "paper:b_method"},
                "experiment_summary": {"text": "The experiment is evidence-bound.", "evidence_ref": "paper:b_method"},
                "limitations": {"text": "INSUFFICIENT_EVIDENCE", "evidence_ref": ""},
            }

    def item(index: int, *, claim_type: str = "FORMULA_CONTEXT") -> EvidencePackItem:
        if claim_type == "METHOD":
            return EvidencePackItem(
                claim_id="c_method",
                claim_type="METHOD",
                evidence_ref="paper:b_method",
                passage_id="p_method",
                passage_text="The method section describes the model and its objective.",
                confidence=0.8,
                token_count=9,
            )
        return EvidencePackItem(
            claim_id=f"c_formula_{index:03d}",
            claim_type="FORMULA_CONTEXT",
            evidence_ref=f"paper:eq{index:03d}",
            passage_id=f"p_eq{index:03d}",
            passage_text=f"Formula: L_{index}=x_{index}+y_{index}. Context before: method. Context after: explanation.",
            confidence=0.7,
            token_count=10,
            formula_origin="mineru_latex",
            formula_id=f"formula_{index:03d}",
            formula_ocr_status="not_required",
        )

    normal_pack = EvidencePack(
        paper_id="paper",
        items=[item(0, claim_type="METHOD"), *[item(i) for i in range(1, 6)]],
        total_tokens=59,
    )
    formula_pack = EvidencePack(
        paper_id="paper",
        items=[item(i) for i in range(1, 8)],
        total_tokens=70,
    )
    skeleton = PaperSkeleton(
        paper_id="paper",
        title="Formula Heavy Paper",
        abstract_summary="A formula-heavy paper.",
        problem="A method problem.",
        method_overview="A method with multiple equations.",
        experiment_overview="Evidence-bound experiment.",
    )
    summary = EvidencePackSummary(
        included_claim_ids=[entry.claim_id for entry in normal_pack.items],
        excluded_claim_ids=[],
        total_tokens=normal_pack.total_tokens,
        claim_type_counts={"METHOD": 1, "FORMULA_CONTEXT": 5},
    )
    client = EmptyFormulaBatchLLM()
    runner = SinglePaperIngestionRunner(
        workspace=WorkspaceStore(tmp_path / "workspace"),
        jobs=JobStore(tmp_path / "jobs.sqlite3"),
        llm_client=client,
    )

    cards, status = runner._run_v2_builders(
        "paper",
        normal_pack,
        formula_pack,
        None,
        None,
        skeleton,
        summary,
    )

    formula_cards = cards["formula_cards"].formula_cards
    assert status.status == "SUCCESS"
    assert [len(batch) for batch in client.formula_prompt_refs] == [5, 2]
    assert len(formula_cards) == 7
    assert {card.formula_id for card in formula_cards} == {f"formula_{i:03d}" for i in range(1, 8)}
    assert all(card.coverage_status == "SUMMARY_ONLY" for card in formula_cards)
