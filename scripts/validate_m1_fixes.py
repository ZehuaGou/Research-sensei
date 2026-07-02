"""Validate M1 pipeline code changes end-to-end without running MinerU inference.

This script proves:
1. formula_slots.json contains all M2 contract fields
2. canonical_paper.md suppresses page header/footer blocks
3. M1ArtifactReader can load the complete bundle
4. Quality gate handles raw-only formula dense papers correctly
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.pipeline import M1CanonicalPipeline
from researchsensei.canonical.canonical_builder import CanonicalBuilder
from researchsensei.canonical.quality_gate import M1QualityGate
from researchsensei.schemas.enums import CanonicalQualityStatus


def make_blocks() -> list[CanonicalDocumentBlock]:
    """Create blocks simulating a real paper with headers/footers/formulas."""
    blocks: list[CanonicalDocumentBlock] = []
    ro = 0

    def add(page, block_type, text="", latex="", section="", bbox=None):
        nonlocal ro
        ro += 1
        blocks.append(CanonicalDocumentBlock(
            block_id=f"b{ro:04d}",
            page=page,
            bbox=bbox or [10, 20, 110, 40],
            block_type=block_type,
            text=text,
            latex=latex,
            reading_order=ro,
            source="mineru25pro",
            section=section,
        ))

    # Page 1: title, abstract
    add(1, "title", "EdgeConvFormer Paper", section="")
    add(1, "text", "We propose EdgeConvFormer for anomaly detection.", section="Abstract")

    # Pages 2-20: simulate page headers/footers
    for p in range(2, 21):
        add(p, "title", "EdgeConvFormer")  # repeated page header
        add(p, "text", f"Content on page {p}.", section="Method" if p > 5 else "Introduction")
        add(p, "text", f"Page {p} of 20")  # page footer
        add(p, "text", "Jie Liu et al.: Preprint submitted to Elsevier")  # author footer

    # Formulas in Method section
    add(6, "title", "3 Method", section="Method")
    add(6, "text", "We define the transformation as:", section="Method")
    add(7, "formula", "", latex="x_t = f(h_t)", section="Method")
    add(7, "formula", "", latex="\\tag{2} y_t = g(x_t)", section="Method")
    add(8, "formula", "", latex="p(x|z) = \\mathcal{N}(x; \\mu_z, \\sigma^2)", section="Method")
    add(8, "formula", "", latex="L = \\mathbb{E}[\\log p(x|z)]", section="Method")
    add(9, "formula", "", latex="\\nabla_{\\theta} L = \\sum_i \\nabla_{\\theta} l_i", section="Method")
    add(9, "formula", "", latex="\\tag{6} p(z_{t+1}|z_t) = \\mathcal{N}(z_t, \\sigma^2 I)", section="Method")
    add(10, "formula", "", latex="ELBO = L - KL(q(z|x) || p(z))", section="Method")
    add(10, "formula", "", latex="p(x_t|z_{t=0}) = \\prod_t p(x_t|z_t)", section="Method")
    add(10, "text", "The model architecture uses attention mechanisms.", section="Method")

    return blocks


def main():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="m1_validate_"))
    print(f"Working directory: {tmp}")

    blocks = make_blocks()

    # Test 1: Run pipeline
    print("\n=== Test 1: Pipeline produces M2-contract formula_slots ===")
    pipeline = M1CanonicalPipeline()
    result = pipeline.run_from_blocks(
        paper_id="2312_01729v1",
        title="EdgeConvFormer Paper",
        blocks=blocks,
        output_dir=tmp,
    )

    slots = json.loads((tmp / "formula_slots.json").read_text(encoding="utf-8"))
    contract_fields = [
        "formula_id", "block_id", "page", "section", "final_origin", "risk_flags",
        "equation_number", "equation_group_id", "group_order", "group_crop_path",
        "nearby_text_before", "nearby_text_after",
    ]
    all_present = True
    for slot in slots:
        for field in contract_fields:
            if field not in slot:
                print(f"  FAIL: slot {slot.get('formula_id')} missing {field}")
                all_present = False
    if all_present:
        print(f"  PASS: All {len(slots)} slots have all M2 contract fields")
    else:
        print("  FAIL: Some slots missing M2 contract fields")
        return 1

    # Check equation_number extraction
    eq_numbers = {s["formula_id"]: s["equation_number"] for s in slots}
    print(f"  Equation numbers: {eq_numbers}")

    # Test 2: Canonical markdown suppresses page headers/footers
    print("\n=== Test 2: Canonical markdown suppresses page headers/footers ===")
    canonical = (tmp / "canonical_paper.md").read_text(encoding="utf-8")
    # The unique page-1 title "### EdgeConvFormer Paper" is legitimate; only repeated headers must be absent
    header_count = canonical.count("### EdgeConvFormer\n")
    footer_count = len([l for l in canonical.splitlines() if "Page " in l and " of 20" in l])
    author_count = canonical.count("Preprint submitted to Elsevier")
    unknown_after_refs = "## Unknown" in canonical.split("## References")[-1] if "## References" in canonical else False

    print(f"  Page header headings: {header_count} (expected 0)")
    print(f"  Footer lines: {footer_count} (expected 0)")
    print(f"  Author footer lines: {author_count} (expected 0)")
    print(f"  Unknown after References: {unknown_after_refs} (expected False)")

    if header_count == 0 and footer_count == 0 and author_count == 0 and not unknown_after_refs:
        print("  PASS: All page headers/footers suppressed")
    else:
        print("  FAIL: Some page headers/footers still in canonical")
        return 1

    # Test 3: M2 bundle artifacts
    print("\n=== Test 3: Generate M2 bundle artifacts ===")
    _write_m2_artifacts(tmp, result, slots)
    from researchsensei.m2.artifact_reader import M1ArtifactReader
    try:
        bundle = M1ArtifactReader(tmp).load()
        print(f"  PASS: M1ArtifactReader loaded successfully")
        print(f"  Contract status: {bundle.contract['status']}")
        print(f"  Formula slots: {len(bundle.formula_slots)}")
        print(f"  Missing fields: {bundle.contract.get('missing_slot_fields', [])}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Test 4: Raw-only formula dense paper
    print("\n=== Test 4: Raw-only formula dense = DEGRADED ===")
    raw_blocks = [
        CanonicalDocumentBlock(
            block_id=f"r{i:03d}", page=1, bbox=[10, 20, 110, 40],
            block_type="formula", text=f"raw formula {i}", reading_order=i,
            source="pymupdf",
        )
        for i in range(8)
    ]
    gate = M1QualityGate()
    gate_result = gate.evaluate(raw_blocks, [])
    print(f"  Status: {gate_result.status.value}")
    print(f"  raw_only_formula_dense: {gate_result.raw_only_formula_dense}")
    print(f"  m2_ready_for_formula_understanding: {gate_result.m2_ready_for_formula_understanding}")
    if gate_result.status != CanonicalQualityStatus.PASS and gate_result.raw_only_formula_dense:
        print("  PASS: Raw-only formula dense paper correctly gated")
    else:
        print("  FAIL: Expected DEGRADED/FAIL for raw-only dense formulas")
        return 1

    # Test 5: Quality gate result for normal paper
    print("\n=== Test 5: Quality gate for normal paper ===")
    print(f"  Quality status: {result.quality.status.value}")
    print(f"  Formula count: {result.quality.formula_count}")
    print(f"  Latex count: {result.quality.latex_count}")
    print(f"  Raw only: {result.quality.raw_only_formula_dense}")
    print(f"  m2_ready: {result.canonicalization.m2_ready}")
    print(f"  Blocking reasons: {result.quality.blocking_reasons}")
    print(f"  Warning reasons: {result.quality.warning_reasons}")

    print("\n=== ALL VALIDATION TESTS PASSED ===")
    return 0


def _write_m2_artifacts(output_dir, result, slots):
    paper_metadata = {
        "paper_id": "2312_01729v1",
        "title": "EdgeConvFormer Paper",
        "arxiv_id": "2312.01729",
        "authors": ["Jie Liu"],
        "pdf_url": "",
        "primary_parser": "mineru25pro",
        "published": "2023-12",
        "pages": 20,
    }
    (output_dir / "paper_metadata.json").write_text(
        json.dumps(paper_metadata, indent=2), encoding="utf-8",
    )
    quality_lines = [
        "# Quality Report",
        f"- canonical_quality_status: {result.quality.status.value}",
        f"- m2_ready: {result.canonicalization.m2_ready}",
        "## Blocking Reasons",
    ]
    for r in result.quality.blocking_reasons:
        quality_lines.append(f"- {r}")
    if not result.quality.blocking_reasons:
        quality_lines.append("- (none)")
    quality_lines.append("## Warning Reasons")
    for r in result.quality.warning_reasons:
        quality_lines.append(f"- {r}")
    if not result.quality.warning_reasons:
        quality_lines.append("- (none)")
    (output_dir / "quality_report.md").write_text("\n".join(quality_lines), encoding="utf-8")
    perf_report = {
        "primary_parser": "mineru25pro",
        "quality_status": result.quality.status.value,
        "m2_ready": result.canonicalization.m2_ready,
        "formula_count": result.quality.formula_count,
        "runtime_seconds": 1.0,
        "blocking_reasons": result.quality.blocking_reasons,
        "warning_reasons": result.quality.warning_reasons,
        "perf_pass": not result.quality.blocking_reasons,
        "warnings": result.quality.warning_reasons,
    }
    (output_dir / "performance_report.json").write_text(
        json.dumps(perf_report, indent=2), encoding="utf-8",
    )
    audit_dir = output_dir / "visual_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    for slot in slots:
        fid = slot.get("formula_id", "unknown")
        (audit_dir / f"{fid}.html").write_text(
            f"<html><body><h1>{fid}</h1><pre>{json.dumps(slot, indent=2)}</pre></body></html>",
            encoding="utf-8",
        )


if __name__ == "__main__":
    raise SystemExit(main())
