"""Tests for M1-to-M2 artifact contract compliance."""
from __future__ import annotations

import json
from pathlib import Path


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


def _make_test_pdf(path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((24, 35), "3 Method", fontsize=12)
    page.insert_text((24, 60), "x_t = f(h_t)", fontsize=12)
    doc.save(path)
    doc.close()


def test_m1_output_loadable_by_m2_artifact_reader(tmp_path) -> None:
    """Pipeline output must be loadable by M1ArtifactReader without FileNotFoundError."""
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    pdf_path = tmp_path / "source.pdf"
    _make_test_pdf(pdf_path)
    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="We study anomaly detection methods.", section="Abstract"),
        _block("b003", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
        _block("b005", page=3, block_type="formula", latex="\\tag{2} y_t=g(x_t)", section="Method"),
        _block("b006", page=3, block_type="text", text="We define the loss as L=E[log p(x)].", section="Method"),
        _block("b007", page=3, block_type="formula", latex="L=E[\\log p(x|z)]", section="Method"),
        _block("b008", page=3, block_type="formula", latex="p(x|z)=N(x;\\mu_z,\\sigma^2)", section="Method"),
        _block("b009", page=3, block_type="formula", latex="\\nabla L = \\sum_i \\nabla l_i", section="Method"),
        _block("b010", page=4, block_type="title", text="4 Experiments", section="Experiments"),
        _block("b011", page=4, text="We evaluate on CIFAR-10.", section="Experiments"),
    ]

    # Provide reviewed_slots with crop/overlay paths to satisfy quality gate
    reviewed_slots = []
    for idx, b in enumerate(blocks):
        if b.block_type == "formula":
            reviewed_slots.append({
                "formula_id": f"formula_{len(reviewed_slots)+1:03d}",
                "block_id": b.block_id,
                "page": b.page,
                "bbox": b.bbox,
                "crop_required": True,
                "overlay_required": True,
                "crop_path": f"formula_crops/{b.block_id}.png",
                "overlay_path": f"formula_overlays/{b.block_id}.png",
                "source_mismatch": False,
            })

    # Add M2 contract fields to reviewed_slots
    for slot in reviewed_slots:
        slot["equation_number"] = ""
        slot["equation_group_id"] = "eq_group_001"
        slot["group_order"] = 1
        slot["group_crop_path"] = ""
        slot["nearby_text_before"] = "Context before formula."
        slot["nearby_text_after"] = "Context after formula."
        slot["section"] = "Method"
        slot["section_confidence"] = "high"
        slot["section_reason"] = "test"
        slot["block_source"] = "mineru25pro"
        slot["final_origin"] = "parser_latex"
        slot["risk_flags"] = []

    # Create crop/overlay files
    crop_dir = tmp_path / "formula_crops"
    overlay_dir = tmp_path / "formula_overlays"
    crop_dir.mkdir(exist_ok=True)
    overlay_dir.mkdir(exist_ok=True)
    for slot in reviewed_slots:
        (tmp_path / slot["crop_path"]).write_bytes(b"\x89PNG")
        (tmp_path / slot["overlay_path"]).write_bytes(b"\x89PNG")

    result = M1CanonicalPipeline().run_from_blocks(
        paper_id="p-m2-contract",
        title="M2 Contract Test Paper",
        blocks=blocks,
        output_dir=tmp_path,
        source_pdf_path=str(pdf_path),
        formula_slots=reviewed_slots,
    )

    assert result.quality.status.value == "PASS"

    # Now write the M2 bundle artifacts (same as acceptance script does)
    _write_m2_artifacts(tmp_path, result)

    # M1ArtifactReader should load without error
    from researchsensei.m2.artifact_reader import M1ArtifactReader

    bundle = M1ArtifactReader(tmp_path).load()
    assert bundle.contract["status"] == "PASS"
    assert len(bundle.formula_slots) == 5
    slot = bundle.formula_slots[0]
    assert "equation_number" in slot
    assert "equation_group_id" in slot
    assert "nearby_text_before" in slot


def test_formula_slot_has_all_m2_contract_fields(tmp_path) -> None:
    """Every formula slot must have all FORMULA_SLOT_CONTRACT_FIELDS keys."""
    from researchsensei.canonical.pipeline import M1CanonicalPipeline
    from researchsensei.m2.artifact_reader import FORMULA_SLOT_CONTRACT_FIELDS

    pdf_path = tmp_path / "source.pdf"
    _make_test_pdf(pdf_path)
    blocks = [
        _block("b001", page=1, block_type="title", text="Abstract"),
        _block("b002", page=1, text="Abstract text.", section="Abstract"),
        _block("b003", page=3, block_type="title", text="3 Method", section="Method"),
        _block("b004", page=3, block_type="formula", latex="x_t=f(h_t)", section="Method"),
        _block("b005", page=3, block_type="formula", latex="y=g(x)", section="Method"),
        _block("b006", page=3, block_type="formula", latex="L=E[\\log p]", section="Method"),
        _block("b007", page=3, block_type="formula", latex="p=N(x;\\mu,\\sigma)", section="Method"),
        _block("b008", page=3, block_type="formula", latex="\\nabla L=0", section="Method"),
        _block("b009", page=3, block_type="text", text="Method description.", section="Method"),
    ]

    M1CanonicalPipeline().run_from_blocks(
        paper_id="p-contract-fields",
        title="Contract Fields Test",
        blocks=blocks,
        output_dir=tmp_path,
        source_pdf_path=str(pdf_path),
    )

    slots = json.loads((tmp_path / "formula_slots.json").read_text(encoding="utf-8"))
    for slot in slots:
        for field in FORMULA_SLOT_CONTRACT_FIELDS:
            assert field in slot, f"Slot {slot.get('formula_id')} missing field: {field}"


def _write_m2_artifacts(output_dir: Path, result) -> None:
    """Write the M2 bundle artifacts that the acceptance script generates."""
    paper_metadata = {
        "paper_id": "p-m2-contract",
        "title": "M2 Contract Test Paper",
        "arxiv_id": "test/12345",
        "authors": ["Test Author"],
        "pdf_url": "",
        "primary_parser": "mineru25pro",
        "published": "2024-01-01",
        "pages": 5,
    }
    (output_dir / "paper_metadata.json").write_text(
        json.dumps(paper_metadata, indent=2), encoding="utf-8",
    )
    quality_lines = [
        "# Quality Report",
        "",
        f"- canonical_quality_status: {result.quality.status.value}",
        f"- m2_ready: {result.canonicalization.m2_ready}",
        "",
        "## Blocking Reasons",
        "- (none)",
        "",
        "## Warning Reasons",
        "- (none)",
    ]
    (output_dir / "quality_report.md").write_text("\n".join(quality_lines), encoding="utf-8")
    perf_report = {
        "primary_parser": "mineru25pro",
        "quality_status": result.quality.status.value,
        "m2_ready": result.canonicalization.m2_ready,
        "formula_count": result.quality.formula_count,
        "runtime_seconds": 1.0,
        "blocking_reasons": [],
        "warning_reasons": [],
        "perf_pass": True,
        "warnings": [],
    }
    (output_dir / "performance_report.json").write_text(
        json.dumps(perf_report, indent=2), encoding="utf-8",
    )
    audit_dir = output_dir / "visual_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "index.html").write_text("<html><body>audit</body></html>", encoding="utf-8")
