"""Re-process paper_1 with the correct Anomaly Transformer PDF (arXiv 2110.02642).

Replaces paper_1/source.pdf with the correct PDF and re-runs the full M1 pipeline.
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUTPUT_DIR = Path(__file__).resolve().parent

PAPER_1_INFO = {
    "src": ROOT / "reports" / "m1_parser_review" / "paper_1" / "source.pdf",
    "pid": "2110.02642",
    "title": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
    "authors": ["Jiehui Xu", "Haixu Wu", "Jianmin Wang", "Mingsheng Long"],
    "year": 2022,
    "venue": "ICLR 2022",
}

STANDARD_SECTIONS = [
    "Abstract", "Introduction", "Related Work", "Method",
    "Experiments", "Conclusion", "References",
]


def main():
    from eval_all_papers import (
        run_body_pipeline, run_formula_detection, run_formula_crop,
        run_formula_merge, generate_artifacts, generate_report,
        run_canonical_normalizer,
    )

    paper_info = PAPER_1_INFO
    pdf_path = paper_info["src"]
    out_dir = OUTPUT_DIR / "paper_1"

    print("=" * 60)
    print(f"Re-processing paper_1 with correct PDF")
    print(f"PDF: {pdf_path}")
    print(f"Title: {paper_info['title']}")
    print("=" * 60)

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return

    # Verify PDF content
    import fitz
    doc = fitz.open(str(pdf_path))
    first_text = doc[0].get_text()
    doc.close()
    if "ANOMALY TRANSFORMER" not in first_text.upper():
        print(f"WARNING: PDF does not appear to be Anomaly Transformer!")
        print(f"First page text: {first_text[:200]}")
        return
    print("PDF verified: Anomaly Transformer")

    # Clean old artifacts
    for f in ["formula_slots.json", "formula_slots.md", "formula_ocr_results.md",
              "REPORT.md", "canonical_paper.md", "markitdown.md", "pymupdf.txt"]:
        p = out_dir / f
        if p.exists():
            p.unlink()
            print(f"  Removed old {f}")

    # Remove old formula_crops and formula_overlays
    for d in ["formula_crops", "formula_overlays"]:
        dp = out_dir / d
        if dp.exists():
            shutil.rmtree(dp)
            print(f"  Removed old {d}/")

    # Step 1: Body pipeline
    print("\n--- STEP 1: Body Pipeline ---")
    body_result = run_body_pipeline(pdf_path)

    # Step 2: Formula detection
    print("\n--- STEP 2: Formula Detection ---")
    formula_slots = run_formula_detection(pdf_path)

    # Step 3: Formula cropping
    print("\n--- STEP 3: Formula Cropping ---")
    crop_dir = out_dir / "formula_crops"
    formula_slots = run_formula_crop(pdf_path, formula_slots, crop_dir)

    # Step 4: Formula merge
    print("\n--- STEP 4: Formula Merge ---")
    text_formulas = body_result.get("formula_candidates", [])
    formula_slots = run_formula_merge(formula_slots, text_formulas)

    # Step 5: Generate artifacts
    print("\n--- STEP 5: Generate Artifacts ---")
    stats = generate_artifacts(body_result, formula_slots, pdf_path, out_dir, paper_info)

    # Step 6: Generate canonical paper
    print("\n--- STEP 6: Generate Canonical Paper ---")
    run_canonical_normalizer(pdf_path, paper_info, out_dir)

    # Step 7: Generate REPORT
    print("\n--- STEP 7: Generate REPORT ---")
    generate_report(body_result, formula_slots, stats, out_dir, paper_info)

    # Re-enrich formula slots with section tracking
    print("\n--- STEP 8: Re-enrich sections ---")
    from researchsensei.canonical.formula_detector import MarkerDocumentFormulaDetector
    from researchsensei.schemas.canonical import FormulaSlot

    detector = MarkerDocumentFormulaDetector()
    slots_path = out_dir / "formula_slots.json"
    with open(slots_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_slots = [FormulaSlot(**s) for s in data]
    detector._enrich_with_pymupdf_context(pdf_path, raw_slots)

    known = sum(1 for s in raw_slots if s.section and s.section not in ("Unknown", ""))
    polluted = sum(1 for s in raw_slots if s.section and s.section != "Unknown" and s.section not in STANDARD_SECTIONS)
    print(f"  section_known: {known}/{len(raw_slots)}")
    print(f"  polluted: {polluted}")

    with open(slots_path, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in raw_slots], f, indent=2, ensure_ascii=False)
    print(f"  Saved enriched formula_slots.json")

    # Summary
    print("\n" + "=" * 60)
    print("paper_1 RE-PROCESSING COMPLETE")
    print("=" * 60)
    print(f"  FormulaSlots: {stats['total_slots']}")
    print(f"  Cropped: {stats['cropped']}")
    print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
    print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")
    print(f"  block_types: {stats['block_type_stats']}")
    print(f"  overlays: {stats.get('overlay_count', 0)}")
    print(f"  section non-empty: {stats.get('section_counts', {}).get('with_section', 0)}/{stats['total_slots']}")


if __name__ == "__main__":
    main()
