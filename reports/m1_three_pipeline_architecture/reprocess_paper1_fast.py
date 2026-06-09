"""Fast re-process paper_1 with correct Anomaly Transformer PDF.

Uses PyMuPDF-based formula detection (no Marker OCR) for speed.
Generates: formula_slots.json, formula_crops/, formula_overlays/,
canonical_paper.md, REPORT.md.
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


def main():
    from eval_all_papers import (
        run_body_pipeline, run_formula_crop, generate_formula_overlays,
        generate_report, _block_type_stats,
    )

    paper_info = PAPER_1_INFO
    pdf_path = paper_info["src"]
    out_dir = OUTPUT_DIR / "paper_1"

    print("=" * 60)
    print(f"Fast re-processing paper_1")
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
        return
    print("PDF verified: Anomaly Transformer")

    # Clean old artifacts
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

    # Step 1: Body pipeline
    print("\n--- STEP 1: Body Pipeline ---")
    body_result = run_body_pipeline(pdf_path)

    # Step 2: PyMuPDF-based formula detection (fast, no Marker OCR)
    print("\n--- STEP 2: PyMuPDF Formula Detection ---")
    from researchsensei.schemas.canonical import FormulaSlot, FormulaOrigin
    from researchsensei.canonical.formula_detector import MarkerDocumentFormulaDetector

    formula_slots = []
    doc = fitz.open(str(pdf_path))
    formula_counter = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block.get("type") != 0:  # text block
                continue
            lines = block.get("lines", [])
            for line in lines:
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    font = span.get("font", "")
                    # Detect math-like content: italic fonts, special chars
                    is_math_font = "italic" in font.lower() or "math" in font.lower()
                    has_math_chars = any(c in text for c in "=∑√σλτπ∈⊙∫∂αβγδ")
                    has_latex = "\\" in text and any(cmd in text for cmd in [
                        "frac", "sum", "int", "partial", "alpha", "beta",
                        "sqrt", "mathcal", "mathbb", "mathrm", "begin",
                    ])

                    if (is_math_font and len(text) > 5 and has_math_chars) or has_latex:
                        formula_counter += 1
                        fid = f"formula_{formula_counter:03d}"
                        bbox = list(span["bbox"])

                        # Get nearby text context
                        block_text = ""
                        for l in lines:
                            for s in l.get("spans", []):
                                block_text += s.get("text", "")

                        slot = FormulaSlot(
                            formula_id=fid,
                            page=page_num,
                            bbox=bbox,
                            block_type="Equation",
                            detection_source="pymupdf",
                            detection_confidence="medium",
                            marker_latex="",
                            final_latex=text,
                            final_origin=FormulaOrigin.RAW_FORMULA_TEXT,
                            crop_path="",
                            ocr_status="skipped",
                            section="Unknown",
                            section_confidence="low",
                            section_source="pymupdf_fallback",
                            section_reason="PyMuPDF-based detection",
                            nearby_text_before=block_text[:200] if block_text else "",
                            nearby_text_after="",
                        )
                        formula_slots.append(slot)

    doc.close()
    print(f"  Detected {len(formula_slots)} formula candidates")

    # Deduplicate by bbox proximity
    deduped = []
    seen_bbox = set()
    for slot in formula_slots:
        bbox_key = (slot.page, round(slot.bbox[0], 0), round(slot.bbox[1], 0))
        if bbox_key not in seen_bbox:
            seen_bbox.add(bbox_key)
            deduped.append(slot)
    formula_slots = deduped
    print(f"  After dedup: {len(formula_slots)} slots")

    # Re-number
    for i, slot in enumerate(formula_slots):
        slot.formula_id = f"formula_{i+1:03d}"

    # Enrich with PyMuPDF context (section, nearby text)
    print("\n--- STEP 2b: Enrich sections ---")
    detector = MarkerDocumentFormulaDetector()
    detector._enrich_with_pymupdf_context(pdf_path, formula_slots)
    known = sum(1 for s in formula_slots if s.section and s.section not in ("Unknown", ""))
    print(f"  section_known: {known}/{len(formula_slots)}")

    # Step 3: Formula cropping
    print("\n--- STEP 3: Formula Cropping ---")
    crop_dir = out_dir / "formula_crops"
    formula_slots = run_formula_crop(pdf_path, formula_slots, crop_dir)

    # Step 4: Generate artifacts
    print("\n--- STEP 4: Generate Artifacts ---")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy source.pdf
    shutil.copy2(pdf_path, out_dir / "source.pdf")

    # Parser outputs
    (out_dir / "markitdown.md").write_text(body_result.get("md_text", ""), encoding="utf-8")
    (out_dir / "pymupdf.txt").write_text(body_result.get("pm_text", ""), encoding="utf-8")

    # formula_slots.json
    slots_data = [s.model_dump() for s in formula_slots]
    (out_dir / "formula_slots.json").write_text(
        json.dumps(slots_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Wrote formula_slots.json ({len(formula_slots)} slots)")

    # formula_slots.md
    md_lines = ["# Formula Slots\n", f"Total: {len(formula_slots)} slots\n"]
    by_origin = {}
    for s in formula_slots:
        origin = s.final_origin.value
        by_origin[origin] = by_origin.get(origin, 0) + 1
    md_lines.append("## Origin Summary\n")
    for origin, count in sorted(by_origin.items()):
        md_lines.append(f"- {origin}: {count}")
    md_lines.append("\n## Slots\n")
    for s in formula_slots:
        bbox_str = str(s.bbox) if s.bbox else "[]"
        md_lines.append(f"### {s.formula_id}")
        md_lines.append(f"- page: {s.page}")
        md_lines.append(f"- bbox: {bbox_str}")
        md_lines.append(f"- block_type: {s.block_type}")
        md_lines.append(f"- final_origin: {s.final_origin.value}")
        if s.marker_latex:
            md_lines.append(f"- marker_latex: `{s.marker_latex[:100]}`")
        if s.final_latex:
            md_lines.append(f"- final_latex: `{s.final_latex[:100]}`")
        md_lines.append("")
    (out_dir / "formula_slots.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  Wrote formula_slots.md")

    # formula_ocr_results.md
    (out_dir / "formula_ocr_results.md").write_text(
        "# Formula OCR Results\n\nOCR is BLOCKED (pix2tex model download too slow).\n",
        encoding="utf-8",
    )

    # formula_overlays
    overlays_dir = out_dir / "formula_overlays"
    overlay_count = generate_formula_overlays(pdf_path, formula_slots, overlays_dir, max_overlays=5)
    if overlay_count == 0:
        overlays_dir.mkdir(exist_ok=True)
        (overlays_dir / "README.md").write_text(
            "No overlays generated.\n", encoding="utf-8",
        )
    print(f"  Generated {overlay_count} formula overlays")

    # Stats
    cropped = sum(1 for s in formula_slots if s.crop_path)
    bt_stats = _block_type_stats(formula_slots)
    by_origin_final = {}
    for s in formula_slots:
        origin = s.final_origin.value
        by_origin_final[origin] = by_origin_final.get(origin, 0) + 1
    slots_with_bbox = sum(1 for s in formula_slots if s.bbox and len(s.bbox) == 4)

    stats = {
        "total_slots": len(formula_slots),
        "cropped": cropped,
        "by_origin": by_origin_final,
        "block_type_stats": bt_stats,
        "crop_paths": [s.crop_path for s in formula_slots if s.crop_path][:10],
        "slots_with_bbox": slots_with_bbox,
        "pages_with_formulas": sorted(set(s.page for s in formula_slots)),
        "overlay_count": overlay_count,
        "section_counts": {
            "with_section": sum(1 for s in formula_slots if s.section),
            "nearby_before": sum(1 for s in formula_slots if s.nearby_text_before),
            "nearby_after": sum(1 for s in formula_slots if s.nearby_text_after),
        },
    }

    # Step 5: Generate canonical_paper.md
    print("\n--- STEP 5: Generate Canonical Paper ---")
    from eval_all_papers import run_canonical_normalizer
    run_canonical_normalizer(pdf_path, paper_info, out_dir)

    # Step 6: Generate REPORT.md
    print("\n--- STEP 6: Generate REPORT ---")
    generate_report(body_result, formula_slots, stats, out_dir, paper_info)

    # Summary
    print("\n" + "=" * 60)
    print("paper_1 FAST RE-PROCESSING COMPLETE")
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
