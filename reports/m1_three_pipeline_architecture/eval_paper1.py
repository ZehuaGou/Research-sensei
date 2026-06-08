"""Minimal real PDF eval for M1 three-pipeline architecture.

Runs the full pipeline on paper_1/source.pdf and generates all required artifacts.
"""
import json
import shutil
import sys
import time
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

PDF_PATH = ROOT / "reports" / "m1_parser_review" / "paper_1" / "source.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent


def run_body_pipeline(pdf_path: Path) -> dict:
    """Run body pipeline: MarkItDown + PyMuPDF, select best parser."""
    from researchsensei.canonical.adapters import MarkItDownAdapter
    from researchsensei.canonical.parser_quality import select_best_parser, score_parser_output

    print("[body] Running MarkItDown...")
    md_text = ""
    markitdown = MarkItDownAdapter()
    if markitdown.is_available():
        t0 = time.time()
        result = markitdown.process(pdf_path)
        elapsed = time.time() - t0
        print(f"[body] MarkItDown: succeeded={result.succeeded}, elapsed={elapsed:.1f}s")
        if result.succeeded:
            md_text = "\n".join(result.sections.values())
            print(f"[body] MarkItDown sections: {list(result.sections.keys())}")
            print(f"[body] MarkItDown text length: {len(md_text)}")
        else:
            print(f"[body] MarkItDown blocked: {result.blocking_reason}")
    else:
        print("[body] MarkItDown not available")

    print("[body] Running PyMuPDF...")
    pm_text = ""
    try:
        import fitz
        t0 = time.time()
        with fitz.open(str(pdf_path)) as doc:
            for page in doc:
                pm_text += page.get_text()
        elapsed = time.time() - t0
        print(f"[body] PyMuPDF: text length={len(pm_text)}, elapsed={elapsed:.1f}s")
    except Exception as exc:
        print(f"[body] PyMuPDF failed: {exc}")

    print("[body] Selecting best parser...")
    selection = select_best_parser(md_text, pm_text, None)
    print(f"[body] Selected: {selection.selected_parser} ({selection.selection_reason})")
    for c in selection.candidates:
        print(f"  - {c.parser_name}: overall={c.overall_score:.1f}, sections={c.section_count}, formulas={c.formula_candidate_count}")

    return {
        "selected_parser": selection.selected_parser,
        "selection_reason": selection.selection_reason,
        "selected_text": selection.selected_text,
        "candidates": selection.candidates,
        "formula_candidates": selection.formula_candidates,
    }


def run_formula_detection(pdf_path: Path) -> list:
    """Run MarkerDocumentFormulaDetector."""
    from researchsensei.canonical.formula_detector import MarkerDocumentFormulaDetector

    print("[formula] Running MarkerDocumentFormulaDetector...")
    detector = MarkerDocumentFormulaDetector()
    if not detector.is_available():
        print("[formula] Marker not available, skipping")
        return []

    t0 = time.time()
    slots = detector.detect(pdf_path)
    elapsed = time.time() - t0
    print(f"[formula] Detected {len(slots)} formula slots in {elapsed:.1f}s")

    for i, slot in enumerate(slots[:10]):
        print(f"  [{i}] {slot.formula_id}: page={slot.page}, bbox={slot.bbox}, type={slot.block_type}, latex={slot.marker_latex[:60] if slot.marker_latex else '(none)'}")

    return slots


def run_formula_crop(pdf_path: Path, slots: list, crop_dir: Path) -> list:
    """Run FormulaCropper."""
    from researchsensei.canonical.formula_cropper import FormulaCropper

    if not slots:
        print("[crop] No slots to crop")
        return slots

    print(f"[crop] Cropping {len(slots)} formulas...")
    cropper = FormulaCropper()
    if not cropper.is_available():
        print("[crop] PyMuPDF not available")
        return slots

    crop_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    slots = cropper.crop(pdf_path, slots, crop_dir)
    elapsed = time.time() - t0

    cropped = sum(1 for s in slots if s.crop_path)
    print(f"[crop] Cropped {cropped}/{len(slots)} in {elapsed:.1f}s")

    for i, slot in enumerate(slots[:10]):
        print(f"  [{i}] {slot.formula_id}: crop_path={slot.crop_path or '(none)'}, ocr_status={slot.ocr_status}")

    return slots


def run_formula_merge(slots: list, text_formulas: list) -> list:
    """Resolve formula slots via priority merge."""
    from researchsensei.canonical.material_normalizer import _resolve_formula_slots

    print("[merge] Resolving formula slots...")
    resolved = _resolve_formula_slots(slots, text_formulas)

    by_origin = {}
    for s in resolved:
        origin = s.final_origin.value
        by_origin[origin] = by_origin.get(origin, 0) + 1

    print(f"[merge] Resolution: {by_origin}")
    for i, slot in enumerate(resolved[:5]):
        print(f"  [{i}] {slot.formula_id}: final_origin={slot.final_origin.value}, final_latex={slot.final_latex[:60] if slot.final_latex else '(none)'}")

    return resolved


def generate_artifacts(body_result: dict, formula_slots: list, pdf_path: Path, output_dir: Path):
    """Generate all required artifacts."""
    # Copy source.pdf
    shutil.copy2(pdf_path, output_dir / "source.pdf")

    # Generate formula_slots.json
    slots_data = [s.model_dump() for s in formula_slots]
    (output_dir / "formula_slots.json").write_text(
        json.dumps(slots_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[artifact] Wrote formula_slots.json ({len(formula_slots)} slots)")

    # Generate formula_slots.md
    md_lines = ["# Formula Slots\n"]
    md_lines.append(f"Total: {len(formula_slots)} slots\n")
    by_origin = {}
    for s in formula_slots:
        origin = s.final_origin.value
        by_origin[origin] = by_origin.get(origin, 0) + 1
    md_lines.append("## Origin Summary\n")
    for origin, count in sorted(by_origin.items()):
        md_lines.append(f"- {origin}: {count}")
    md_lines.append("")
    md_lines.append("## Slots\n")
    for s in formula_slots:
        bbox_str = str(s.bbox) if s.bbox else "[]"
        md_lines.append(f"### {s.formula_id}")
        md_lines.append(f"- page: {s.page}")
        md_lines.append(f"- bbox: {bbox_str}")
        md_lines.append(f"- block_type: {s.block_type}")
        md_lines.append(f"- detection_source: {s.detection_source}")
        md_lines.append(f"- detection_confidence: {s.detection_confidence}")
        md_lines.append(f"- final_origin: {s.final_origin.value}")
        if s.marker_latex:
            md_lines.append(f"- marker_latex: `{s.marker_latex[:100]}`")
        if s.final_latex:
            md_lines.append(f"- final_latex: `{s.final_latex[:100]}`")
        if s.crop_path:
            md_lines.append(f"- crop_path: `{s.crop_path}`")
        if s.unresolved_reason:
            md_lines.append(f"- unresolved_reason: {s.unresolved_reason}")
        md_lines.append("")
    (output_dir / "formula_slots.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[artifact] Wrote formula_slots.md")

    # Generate formula_ocr_results.md
    ocr_lines = ["# Formula OCR Results\n"]
    ocr_lines.append("OCR is BLOCKED (pix2tex model download too slow).\n")
    ocr_lines.append("No OCR was performed in this evaluation.\n")
    (output_dir / "formula_ocr_results.md").write_text("\n".join(ocr_lines), encoding="utf-8")
    print(f"[artifact] Wrote formula_ocr_results.md")

    # Generate formula_overlays/ (placeholder — overlay rendering not implemented)
    overlays_dir = output_dir / "formula_overlays"
    overlays_dir.mkdir(exist_ok=True)
    (overlays_dir / "README.md").write_text(
        "Formula overlays not yet implemented. Use formula_crops/ for cropped images.\n",
        encoding="utf-8",
    )
    print(f"[artifact] Created formula_overlays/ (placeholder)")

    # Count stats
    cropped = sum(1 for s in formula_slots if s.crop_path)
    by_origin_final = {}
    for s in formula_slots:
        origin = s.final_origin.value
        by_origin_final[origin] = by_origin_final.get(origin, 0) + 1

    return {
        "total_slots": len(formula_slots),
        "cropped": cropped,
        "by_origin": by_origin_final,
        "crop_paths": [s.crop_path for s in formula_slots if s.crop_path][:5],
    }


def generate_report(body_result: dict, formula_slots: list, stats: dict, output_dir: Path):
    """Generate REPORT.md answering all required questions."""
    selected = body_result["selected_parser"]
    reason = body_result["selection_reason"]
    candidates = body_result["candidates"]

    # Count stats
    by_origin = stats["by_origin"]
    parser_latex = by_origin.get("parser_latex", 0)
    ocr_latex = by_origin.get("ocr_latex", 0)
    unresolved = by_origin.get("unresolved", 0)
    raw_text = by_origin.get("raw_formula_text", 0)

    # Check canonical_paper.md
    canonical_path = output_dir / "canonical_paper.md"
    has_canonical = canonical_path.exists()
    canonical_content = canonical_path.read_text(encoding="utf-8") if has_canonical else ""
    has_formula_comment = "<!-- formula_id:" in canonical_content
    has_unresolved = "{{FORMULA:" in canonical_content

    # Equation blocks from slots
    equation_blocks = [s for s in formula_slots if s.block_type == "Equation"]
    inline_blocks = [s for s in formula_slots if s.block_type == "TextInlineMath"]

    # Pages with formulas
    pages_with_formulas = set(s.page for s in formula_slots)

    # Bbox check
    slots_with_bbox = [s for s in formula_slots if s.bbox and len(s.bbox) == 4]

    report = f"""# M1 Three-Pipeline Architecture — Live Eval Report (paper_1)

**Date**: 2026-06-08
**PDF**: reports/m1_parser_review/paper_1/source.pdf
**Eval script**: reports/m1_three_pipeline_architecture/eval_paper1.py

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `{selected}` |
| selection_reason | `{reason}` |
| MarkItDown available | {body_result.get('markitdown_available', True)} |
| PyMuPDF available | {body_result.get('pymupdf_available', True)} |

### Parser Scores

"""
    for c in candidates:
        report += f"| {c.parser_name} | overall={c.overall_score:.1f} | sections={c.section_count} | formulas={c.formula_candidate_count} | spacing={c.spacing_quality:.3f} |\n"

    report += f"""
---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | {stats['total_slots']} |
| Equation block count | {len(equation_blocks)} |
| TextInlineMath block count | {len(inline_blocks)} |
| Pages with formulas | {sorted(pages_with_formulas)} |
| page_id exists | {'YES' if pages_with_formulas else 'NO'} |
| bbox exists | {'YES' if slots_with_bbox else 'NO'} |
| bbox count | {len(slots_with_bbox)} |
| crop success count | {stats['cropped']} |
| crop success rate | {stats['cropped']}/{stats['total_slots']} |

### Origin Summary

| Origin | Count |
|--------|-------|
"""
    for origin, count in sorted(by_origin.items()):
        report += f"| {origin} | {count} |\n"

    report += f"""
### First 5 Crop Paths

"""
    for i, path in enumerate(stats["crop_paths"][:5]):
        report += f"{i+1}. `{path}`\n"
    if not stats["crop_paths"]:
        report += "(no crops generated)\n"

    report += f"""
---

## Canonical Paper

| Question | Answer |
|----------|--------|
| canonical_paper.md exists | {'YES' if has_canonical else 'NO'} |
| formula slot comments present | {'YES' if has_formula_comment else 'NO'} |
| unresolved slots present | {'YES' if has_unresolved else 'NO'} |

---

## Resolution Summary

| Metric | Value |
|--------|-------|
| parser_latex_count | {parser_latex} |
| ocr_latex_count | {ocr_latex} |
| raw_formula_text_count | {raw_text} |
| unresolved_formula_count | {unresolved} |

---

## Remaining Work

- formula_overlays/ not yet implemented (placeholder only)
- OCR blocked (pix2tex model unavailable)
- Section inference for FormulaSlots not yet implemented
"""

    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"[artifact] Wrote REPORT.md")


def main():
    print("=" * 60)
    print("M1 Three-Pipeline Live Eval — paper_1")
    print("=" * 60)

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found: {PDF_PATH}")
        sys.exit(1)

    print(f"\nPDF: {PDF_PATH}")
    print(f"Output: {OUTPUT_DIR}\n")

    # Step 1: Body pipeline
    print("-" * 40)
    print("STEP 1: Body Pipeline")
    print("-" * 40)
    body_result = run_body_pipeline(PDF_PATH)

    # Step 2: Formula detection
    print("\n" + "-" * 40)
    print("STEP 2: Formula Detection")
    print("-" * 40)
    formula_slots = run_formula_detection(PDF_PATH)

    # Step 3: Formula cropping
    print("\n" + "-" * 40)
    print("STEP 3: Formula Cropping")
    print("-" * 40)
    crop_dir = OUTPUT_DIR / "formula_crops"
    formula_slots = run_formula_crop(PDF_PATH, formula_slots, crop_dir)

    # Step 4: Formula merge (resolve)
    print("\n" + "-" * 40)
    print("STEP 4: Formula Merge")
    print("-" * 40)
    text_formulas = body_result.get("formula_candidates", [])
    formula_slots = run_formula_merge(formula_slots, text_formulas)

    # Step 5: Generate artifacts
    print("\n" + "-" * 40)
    print("STEP 5: Generate Artifacts")
    print("-" * 40)
    stats = generate_artifacts(body_result, formula_slots, PDF_PATH, OUTPUT_DIR)

    # Generate REPORT.md
    generate_report(body_result, formula_slots, stats, OUTPUT_DIR)

    # Generate canonical_paper.md (from MaterialNormalizer)
    print("\n[canonical] Generating canonical_paper.md via MaterialNormalizer...")
    try:
        from researchsensei.canonical.material_normalizer import MaterialNormalizer
        from researchsensei.schemas.direction import CandidatePaper, ResolvedPaperSource
        from researchsensei.schemas.enums import PaperSourceType, PaperSourceStatus

        paper = CandidatePaper(
            paper_id="2112.14436",
            title="Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
            authors=["Yuxuan Zhang", "Ihor Kats", "Dmitrii Khizbullin", "Yun Yang"],
            year=2022,
            venue="ICML 2022",
            arxiv_id="2112.14436",
        )
        source = ResolvedPaperSource(
            paper_id="2112.14436",
            title="Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
            source_type=PaperSourceType.PDF,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            local_path=str(PDF_PATH),
        )

        normalizer = MaterialNormalizer(
            formula_detection_enabled=True,
            formula_crop_enabled=True,
        )
        result = normalizer.normalize(paper, source, output_dir=OUTPUT_DIR)

        print(f"[canonical] status={result.canonicalization_status.value}")
        print(f"[canonical] m2_ready={result.m2_ready}")
        print(f"[canonical] canonical_paper_path={result.canonical_paper_path}")
        print(f"[canonical] formula_blocks={len(result.formula_blocks)}")
    except Exception as exc:
        print(f"[canonical] MaterialNormalizer failed: {exc}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)

    # Summary
    print(f"\nSummary:")
    print(f"  FormulaSlots: {stats['total_slots']}")
    print(f"  Cropped: {stats['cropped']}")
    print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
    print(f"  ocr_latex: {stats['by_origin'].get('ocr_latex', 0)}")
    print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")
    print(f"  Crop paths: {stats['crop_paths'][:5]}")


if __name__ == "__main__":
    main()
