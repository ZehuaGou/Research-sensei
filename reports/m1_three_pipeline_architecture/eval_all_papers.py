"""Full M1 three-pipeline eval for paper_1, paper_2, paper_3.

Runs Body + Formula + Merger on each paper and generates all required artifacts.
"""
import json
import shutil
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUTPUT_DIR = Path(__file__).resolve().parent

PAPERS = {
    "paper_1": {
        "src": ROOT / "reports" / "m1_parser_review" / "paper_1" / "source.pdf",
        "pid": "2112.14436",
        "title": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
        "authors": ["Yuxuan Zhang", "Ihor Kats", "Dmitrii Khizbullin", "Yun Yang"],
        "year": 2022,
        "venue": "ICML 2022",
    },
    "paper_2": {
        "src": ROOT / "reports" / "m1_parser_review" / "paper_2" / "source.pdf",
        "pid": "W3184127157",
        "title": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
        "authors": ["Wanjie Sun", "Zhe Zhang", "Chenxu Liu", "MiaoZhu"],
        "year": 2024,
        "venue": "IEEE IoT Journal 2024",
    },
    "paper_3": {
        "src": ROOT / "reports" / "m1_parser_review" / "paper_3" / "source.pdf",
        "pid": "2510.18998",
        "title": "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection",
        "authors": ["Yiyuan Yang", "Yixuan Zhang", "Tongliang Liu"],
        "year": 2025,
        "venue": "arXiv 2025",
    },
}


def run_body_pipeline(pdf_path: Path) -> dict:
    """Run body pipeline: MarkItDown + PyMuPDF, select best parser."""
    from researchsensei.canonical.adapters import MarkItDownAdapter
    from researchsensei.canonical.parser_quality import select_best_parser

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
        "md_text": md_text,
        "pm_text": pm_text,
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
        print(f"  [{i}] {slot.formula_id}: page={slot.page}, block_type={slot.block_type}, latex={slot.marker_latex[:60] if slot.marker_latex else '(none)'}")

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


def _block_type_stats(slots: list) -> dict:
    """Count formula slots by block_type."""
    counter = Counter(s.block_type for s in slots)
    return dict(counter)


def generate_formula_overlays(pdf_path: Path, slots: list, overlays_dir: Path, max_overlays: int = 5):
    """Generate overlay PNGs showing bbox rectangles on page images for first N formulas."""
    try:
        import fitz
    except ImportError:
        print("[overlay] PyMuPDF not available")
        return 0

    overlays_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        print(f"[overlay] Failed to open PDF: {exc}")
        return 0

    count = 0
    try:
        # Group slots by page, take first max_overlays formulas
        page_formulas: dict[int, list] = {}
        for slot in slots:
            if not slot.bbox or len(slot.bbox) != 4:
                continue
            page_formulas.setdefault(slot.page, []).append(slot)
            if sum(len(v) for v in page_formulas.values()) >= max_overlays:
                break

        for page_num, page_slots in page_formulas.items():
            page_idx = page_num - 1
            if page_idx < 0 or page_idx >= len(doc):
                continue

            page = doc[page_idx]
            # Render page as pixmap (2x resolution for clarity)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)

            # Create overlay image
            from PIL import Image, ImageDraw
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(img)

            for slot in page_slots:
                fx1, fy1, fx2, fy2 = slot.bbox
                # Scale to pixmap coordinates (2x)
                sx1, sy1, sx2, sy2 = fx1 * 2, fy1 * 2, fx2 * 2, fy2 * 2

                # Draw red rectangle (3px thick)
                for offset in range(3):
                    draw.rectangle(
                        [sx1 - offset, sy1 - offset, sx2 + offset, sy2 + offset],
                        outline="red",
                    )

                # Draw formula_id label
                label = slot.formula_id
                draw.text((sx1, sy1 - 16), label, fill="red")

                count += 1
                if count >= max_overlays:
                    break

            # Save overlay
            overlay_path = overlays_dir / f"overlay_page{page_num}.png"
            img.save(str(overlay_path), "PNG")
            print(f"[overlay] Saved {overlay_path} ({len(page_slots)} formulas)")

            if count >= max_overlays:
                break
    finally:
        doc.close()

    return count


def generate_artifacts(body_result: dict, formula_slots: list, pdf_path: Path, output_dir: Path, paper_info: dict):
    """Generate all required artifacts for a single paper."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy source.pdf
    shutil.copy2(pdf_path, output_dir / "source.pdf")

    # Parser outputs
    (output_dir / "markitdown.md").write_text(body_result.get("md_text", ""), encoding="utf-8")
    (output_dir / "pymupdf.txt").write_text(body_result.get("pm_text", ""), encoding="utf-8")

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

    # Generate formula_overlays/ — draw bbox on page images for first 5 formulas
    overlays_dir = output_dir / "formula_overlays"
    overlay_count = generate_formula_overlays(pdf_path, formula_slots, overlays_dir, max_overlays=5)
    if overlay_count == 0:
        overlays_dir.mkdir(exist_ok=True)
        (overlays_dir / "README.md").write_text(
            "No overlays generated (no valid bbox data or PyMuPDF unavailable).\n",
            encoding="utf-8",
        )
    print(f"[artifact] Generated {overlay_count} formula overlays")

    # Block type stats
    bt_stats = _block_type_stats(formula_slots)

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
        "block_type_stats": bt_stats,
        "crop_paths": [s.crop_path for s in formula_slots if s.crop_path][:10],
        "slots_with_bbox": sum(1 for s in formula_slots if s.bbox and len(s.bbox) == 4),
        "pages_with_formulas": sorted(set(s.page for s in formula_slots)),
        "overlay_count": overlay_count,
        "section_counts": {
            "with_section": sum(1 for s in formula_slots if s.section),
            "nearby_before": sum(1 for s in formula_slots if s.nearby_text_before),
            "nearby_after": sum(1 for s in formula_slots if s.nearby_text_after),
        },
    }


def generate_report(body_result: dict, formula_slots: list, stats: dict, output_dir: Path, paper_info: dict):
    """Generate REPORT.md answering all required questions."""
    selected = body_result["selected_parser"]
    reason = body_result["selection_reason"]
    candidates = body_result["candidates"]
    bt_stats = stats["block_type_stats"]
    sc = stats.get("section_counts", {})

    # Find selected parser score
    selected_score = 0.0
    for c in candidates:
        if c.parser_name == selected:
            selected_score = c.overall_score

    # Check canonical_paper.md
    canonical_path = output_dir / "canonical_paper.md"
    has_canonical = canonical_path.exists()
    canonical_content = canonical_path.read_text(encoding="utf-8") if has_canonical else ""
    has_formula_comment = "<!-- formula_id:" in canonical_content
    has_unresolved = "{{FORMULA:" in canonical_content
    # Count formula comments with empty section
    import re
    formula_comment_pattern = re.compile(r'<!-- formula_id:.*?section:\s*(\S*?)\s*\|')
    empty_section_count = sum(1 for m in formula_comment_pattern.finditer(canonical_content) if not m.group(1))

    report = f"""# M1 Three-Pipeline Architecture — Eval Report ({paper_info['pid']})

**Date**: 2026-06-09
**PDF**: {paper_info['src'].relative_to(ROOT)}
**Title**: {paper_info['title']}

---

## Body Pipeline

| Question | Answer |
|----------|--------|
| body_selected_parser | `{selected}` |
| body parser score | `{selected_score:.1f}` |
| selection_reason | `{reason}` |

### Parser Scores

| parser | overall_score | sections | formulas | spacing |
|--------|--------------|----------|----------|---------|
"""
    for c in candidates:
        report += f"| {c.parser_name} | {c.overall_score:.1f} | {c.section_count} | {c.formula_candidate_count} | {c.spacing_quality:.3f} |\n"

    report += f"""
---

## Formula Pipeline

| Question | Answer |
|----------|--------|
| FormulaSlot total count | {stats['total_slots']} |
| Equation count | {bt_stats.get('Equation', 0)} |
| TextInlineMath count | {bt_stats.get('TextInlineMath', 0)} |
| Math count | {bt_stats.get('Math', 0)} |
| Formula count | {bt_stats.get('Formula', 0)} |
| Unknown formula block count | {sum(v for k, v in bt_stats.items() if k not in ('Equation', 'TextInlineMath', 'Math', 'Formula'))} |
| page_id count | {len(stats['pages_with_formulas'])} |
| bbox count | {stats['slots_with_bbox']} |
| crop success count | {stats['cropped']} |
| crop success rate | {stats['cropped']}/{stats['total_slots']} |
| section non-empty count | {sc.get('with_section', 0)}/{stats['total_slots']} |
| nearby_text_before non-empty | {sc.get('nearby_before', 0)}/{stats['total_slots']} |
| nearby_text_after non-empty | {sc.get('nearby_after', 0)}/{stats['total_slots']} |

### Block Type Distribution

| block_type | count |
|------------|-------|
"""
    for bt, count in sorted(bt_stats.items()):
        report += f"| {bt} | {count} |\n"

    report += f"""
### Origin Summary

| Origin | Count |
|--------|-------|
"""
    for origin, count in sorted(stats["by_origin"].items()):
        report += f"| {origin} | {count} |\n"

    report += f"""
### Crop Paths (first 10)

"""
    for i, path in enumerate(stats["crop_paths"][:10]):
        report += f"{i+1}. `{path}`\n"
    if not stats["crop_paths"]:
        report += "(no crops generated)\n"

    report += f"""
---

## Canonical Paper

| Question | Answer |
|----------|--------|
| canonical_paper.md exists | {'YES' if has_canonical else 'NO'} |
| canonical_paper.md size | {canonical_path.stat().st_size if has_canonical else 0} bytes |
| formula slot comments present | {'YES' if has_formula_comment else 'NO'} |
| unresolved slots present | {'YES' if has_unresolved else 'NO'} |
| formula comments with empty section | {empty_section_count} |

---

## Resolution Summary

| Metric | Value |
|--------|-------|
| parser_latex_count | {stats['by_origin'].get('parser_latex', 0)} |
| ocr_latex_count | {stats['by_origin'].get('ocr_latex', 0)} |
| raw_formula_text_count | {stats['by_origin'].get('raw_formula_text', 0)} |
| unresolved_formula_count | {stats['by_origin'].get('unresolved', 0)} |

---

## Formula Overlays

| Metric | Value |
|--------|-------|
| overlays generated | {stats.get('overlay_count', 0)} |
| overlay_dir | formula_overlays/ |

---

## OCR Status

| Question | Answer |
|----------|--------|
| OCR enabled | NO |
| OCR reason | pix2tex model download too slow; blocked by policy |

---

## Remaining Work

- OCR blocked (pix2tex model unavailable)
"""

    (output_dir / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"[artifact] Wrote REPORT.md")


def run_canonical_normalizer(pdf_path: Path, paper_info: dict, output_dir: Path):
    """Generate canonical_paper.md via MaterialNormalizer."""
    print("[canonical] Generating canonical_paper.md via MaterialNormalizer...")
    try:
        from researchsensei.canonical.material_normalizer import MaterialNormalizer
        from researchsensei.schemas.direction import CandidatePaper, ResolvedPaperSource
        from researchsensei.schemas.enums import PaperSourceType, PaperSourceStatus

        paper = CandidatePaper(
            paper_id=paper_info["pid"],
            title=paper_info["title"],
            authors=paper_info["authors"],
            year=paper_info["year"],
            venue=paper_info["venue"],
            arxiv_id=paper_info["pid"],
        )
        source = ResolvedPaperSource(
            paper_id=paper_info["pid"],
            title=paper_info["title"],
            source_type=PaperSourceType.PDF,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            local_path=str(pdf_path),
        )

        normalizer = MaterialNormalizer(
            formula_detection_enabled=True,
            formula_crop_enabled=True,
        )
        result = normalizer.normalize(paper, source, output_dir=output_dir)

        print(f"[canonical] status={result.canonicalization_status.value}")
        print(f"[canonical] m2_ready={result.m2_ready}")
        print(f"[canonical] formula_blocks={len(result.formula_blocks)}")
        return result
    except Exception as exc:
        print(f"[canonical] MaterialNormalizer failed: {exc}")
        import traceback
        traceback.print_exc()
        return None


def run_one_paper(paper_name: str, paper_info: dict):
    """Run full three-pipeline on one paper."""
    print("\n" + "=" * 60)
    print(f"Processing {paper_name}: {paper_info['title']}")
    print("=" * 60)

    pdf_path = paper_info["src"]
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return None

    out_dir = OUTPUT_DIR / paper_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nPDF: {pdf_path}")
    print(f"Output: {out_dir}\n")

    # Step 1: Body pipeline
    print("-" * 40)
    print("STEP 1: Body Pipeline")
    print("-" * 40)
    body_result = run_body_pipeline(pdf_path)

    # Step 2: Formula detection
    print("\n" + "-" * 40)
    print("STEP 2: Formula Detection")
    print("-" * 40)
    formula_slots = run_formula_detection(pdf_path)

    # Step 3: Formula cropping
    print("\n" + "-" * 40)
    print("STEP 3: Formula Cropping")
    print("-" * 40)
    crop_dir = out_dir / "formula_crops"
    formula_slots = run_formula_crop(pdf_path, formula_slots, crop_dir)

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
    stats = generate_artifacts(body_result, formula_slots, pdf_path, out_dir, paper_info)

    # Step 6: Generate canonical_paper.md (must run BEFORE REPORT so canonical exists)
    print("\n" + "-" * 40)
    print("STEP 6: Generate Canonical Paper")
    print("-" * 40)
    run_canonical_normalizer(pdf_path, paper_info, out_dir)

    # Step 7: Generate REPORT.md (AFTER canonical so file-existence check is accurate)
    print("\n" + "-" * 40)
    print("STEP 7: Generate REPORT")
    print("-" * 40)
    generate_report(body_result, formula_slots, stats, out_dir, paper_info)

    print(f"\n{paper_name} DONE")
    print(f"  FormulaSlots: {stats['total_slots']}")
    print(f"  Cropped: {stats['cropped']}")
    print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
    print(f"  ocr_latex: {stats['by_origin'].get('ocr_latex', 0)}")
    print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")
    print(f"  block_types: {stats['block_type_stats']}")
    print(f"  overlays: {stats.get('overlay_count', 0)}")
    print(f"  section non-empty: {stats.get('section_counts', {}).get('with_section', 0)}/{stats['total_slots']}")
    print(f"  nearby_before non-empty: {stats.get('section_counts', {}).get('nearby_before', 0)}/{stats['total_slots']}")

    return stats


def main():
    print("=" * 60)
    print("M1 Three-Pipeline Full Eval — paper_1, paper_2, paper_3")
    print("=" * 60)

    all_stats = {}
    for paper_name, paper_info in PAPERS.items():
        stats = run_one_paper(paper_name, paper_info)
        if stats:
            all_stats[paper_name] = stats

    # Summary
    print("\n" + "=" * 60)
    print("ALL PAPERS COMPLETE")
    print("=" * 60)
    for paper_name, stats in all_stats.items():
        print(f"\n{paper_name}:")
        print(f"  FormulaSlots: {stats['total_slots']}")
        print(f"  Cropped: {stats['cropped']}")
        print(f"  block_types: {stats['block_type_stats']}")
        print(f"  parser_latex: {stats['by_origin'].get('parser_latex', 0)}")
        print(f"  ocr_latex: {stats['by_origin'].get('ocr_latex', 0)}")
        print(f"  unresolved: {stats['by_origin'].get('unresolved', 0)}")


if __name__ == "__main__":
    main()
