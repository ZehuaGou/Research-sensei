"""Re-process paper_1 ONLY with Marker-based formula detection.

Reads from m1_parser_review/paper_1/source.pdf (correct Anomaly Transformer).
Outputs to m1_three_pipeline_architecture/paper_1/.
"""
import json
import shutil
import sys
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


def main():
    from eval_all_papers import run_one_paper

    print("=" * 60)
    print("Re-processing paper_1 with Marker (full pipeline)")
    print(f"PDF: {PAPER_1_INFO['src']}")
    print(f"Title: {PAPER_1_INFO['title']}")
    print("=" * 60)

    if not PAPER_1_INFO["src"].exists():
        print(f"ERROR: PDF not found: {PAPER_1_INFO['src']}")
        return

    # Verify PDF
    import fitz
    doc = fitz.open(str(PAPER_1_INFO["src"]))
    first_text = doc[0].get_text()
    doc.close()
    if "ANOMALY TRANSFORMER" not in first_text.upper():
        print("WARNING: PDF does not appear to be Anomaly Transformer!")
        return
    print("PDF verified: Anomaly Transformer")

    # Clean old paper_1 artifacts
    out_dir = OUTPUT_DIR / "paper_1"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in ["formula_slots.json", "formula_slots.md", "formula_ocr_results.md",
              "REPORT.md", "canonical_paper.md", "markitdown.md", "pymupdf.txt"]:
        p = out_dir / f
        if p.exists():
            p.unlink()
            print(f"  Removed old {f}")
    for d in ["formula_crops", "formula_overlays"]:
        dp = out_dir / d
        if dp.exists():
            shutil.rmtree(dp)
            print(f"  Removed old {d}/")

    # Run full pipeline for paper_1 only
    stats = run_one_paper("paper_1", PAPER_1_INFO)

    if stats:
        print("\n" + "=" * 60)
        print("paper_1 RE-PROCESSING COMPLETE")
        print("=" * 60)
        print(f"  FormulaSlots: {stats['total_slots']}")
        print(f"  Cropped: {stats['cropped']}")
        print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
        print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")
        print(f"  overlays: {stats.get('overlay_count', 0)}")
    else:
        print("ERROR: paper_1 processing failed")


if __name__ == "__main__":
    main()
