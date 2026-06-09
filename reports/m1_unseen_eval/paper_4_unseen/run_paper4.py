"""Run full M1 pipeline on paper_4_unseen (MEMTO, arXiv 2312.02530).

Blind eval — new unseen paper to verify M1 works beyond the original 3 papers.
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reports" / "m1_three_pipeline_architecture"))

OUTPUT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports" / "m1_three_pipeline_architecture"

PAPER_4_INFO = {
    "src": OUTPUT_DIR / "source.pdf",
    "pid": "2312.02530",
    "title": "MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection",
    "authors": ["Junho Song", "Keonwoo Kim", "Jeonglyul Oh", "Sungzoon Cho"],
    "year": 2023,
    "venue": "arXiv 2023",
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

    paper_info = PAPER_4_INFO
    pdf_path = paper_info["src"]
    out_dir = OUTPUT_DIR

    print("=" * 60)
    print(f"M1 Pipeline: paper_4_unseen")
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
    if "MEMTO" not in first_text.upper():
        print(f"WARNING: PDF does not appear to be MEMTO!")
        print(f"First page text: {first_text[:300]}")
        return
    print("PDF verified: MEMTO")

    # Step 1: Body pipeline
    print("\n--- STEP 1: Body Pipeline ---")
    body_result = run_body_pipeline(pdf_path)

    # Step 2: Formula detection
    print("\n--- STEP 2: Formula Detection ---")
    formula_slots = run_formula_detection(pdf_path)

    # Step 3: Formula cropping
    print("\n--- STEP 3: Formula Cropping ---")
    crop_dir = out_dir / "formula_crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    formula_slots = run_formula_crop(pdf_path, formula_slots, crop_dir)

    # Step 4: Formula merge
    print("\n--- STEP 4: Formula Merge ---")
    text_formulas = body_result.get("formula_candidates", [])
    formula_slots = run_formula_merge(formula_slots, text_formulas)

    # Step 5: Generate artifacts (includes overlays)
    print("\n--- STEP 5: Generate Artifacts ---")
    stats = generate_artifacts(body_result, formula_slots, pdf_path, out_dir, paper_info)

    # Step 6: Generate canonical paper
    print("\n--- STEP 6: Generate Canonical Paper ---")
    run_canonical_normalizer(pdf_path, paper_info, out_dir)

    # Step 7: Generate REPORT
    print("\n--- STEP 7: Generate REPORT ---")
    generate_report(body_result, formula_slots, stats, out_dir, paper_info)

    # Step 8: Enrich sections with PyMuPDF context
    print("\n--- STEP 8: Enrich Sections ---")
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

    # Step 9: Ensure overlays for ALL pages
    print("\n--- STEP 9: Ensure All Overlays ---")
    from generate_visual_audit import ensure_overlays
    overlays_dir = out_dir / "formula_overlays"
    overlay_count = ensure_overlays("paper_4_unseen", [s.model_dump() for s in raw_slots], pdf_path, overlays_dir)
    print(f"  Overlays: {overlay_count}")

    # Summary
    print("\n" + "=" * 60)
    print("paper_4_unseen COMPLETE")
    print("=" * 60)
    print(f"  FormulaSlots: {stats['total_slots']}")
    print(f"  Cropped: {stats['cropped']}")
    print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
    print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")
    print(f"  block_types: {stats['block_type_stats']}")
    print(f"  overlays: {stats.get('overlay_count', 0)}")
    print(f"  section known: {known}/{len(raw_slots)}")
    print(f"  polluted: {polluted}")


if __name__ == "__main__":
    main()
