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
