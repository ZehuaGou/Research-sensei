"""Generate visual audit HTML pages for all M1 formula slots.

Creates:
- visual_audit/index.html (summary landing page)
- visual_audit/paper_1.html (3 formulas)
- visual_audit/paper_2.html (16 formulas)
- visual_audit/paper_3.html (18 formulas)
- visual_audit/SUMMARY.md (full table)
- Missing overlay PNGs for all pages with formulas
"""
import base64
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUTPUT_DIR = Path(__file__).resolve().parent
AUDIT_DIR = OUTPUT_DIR / "visual_audit"

PAPERS = {
    "paper_1": {
        "pid": "2112.14436",
        "title": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
    },
    "paper_2": {
        "pid": "W3184127157",
        "title": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
    },
    "paper_3": {
        "pid": "2510.18998",
        "title": "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection",
    },
}


def ensure_overlays(paper_name: str, slots: list, pdf_path: Path, overlays_dir: Path):
    """Generate overlay PNGs for ALL pages that have formulas."""
    import fitz
    from PIL import Image, ImageDraw

    overlays_dir.mkdir(parents=True, exist_ok=True)

    # Group slots by page
    page_formulas: dict[int, list] = defaultdict(list)
    for slot in slots:
        bbox = slot.get("bbox", []) if isinstance(slot, dict) else slot.bbox
        page = slot.get("page", 0) if isinstance(slot, dict) else slot.page
        if bbox and len(bbox) == 4:
            page_formulas[page].append(slot)

    doc = fitz.open(str(pdf_path))
    generated = 0
    for page_num, page_slots in sorted(page_formulas.items()):
        overlay_path = overlays_dir / f"overlay_page{page_num}.png"
        if overlay_path.exists():
            generated += 1
            continue

        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            continue

        page = doc[page_idx]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)

        for slot in page_slots:
            bbox = slot.get("bbox", []) if isinstance(slot, dict) else slot.bbox
            fid = slot.get("formula_id", "") if isinstance(slot, dict) else slot.formula_id
            fx1, fy1, fx2, fy2 = bbox
            sx1, sy1, sx2, sy2 = fx1 * 2, fy1 * 2, fx2 * 2, fy2 * 2
            for offset in range(3):
                draw.rectangle(
                    [sx1 - offset, sy1 - offset, sx2 + offset, sy2 + offset],
                    outline="red",
                )
            draw.text((sx1, sy1 - 16), fid, fill="red")

        img.save(str(overlay_path), "PNG")
        generated += 1
        print(f"  [overlay] Generated {overlay_path.name} ({len(page_slots)} formulas)")

    doc.close()
    return generated


def extract_canonical_formulas(canonical_path: Path) -> dict[str, str]:
    """Extract formula comments and LaTeX from canonical_paper.md."""
    if not canonical_path.exists():
        return {}

    content = canonical_path.read_text(encoding="utf-8")
    formulas = {}

    # Find all formula_id comments
    pattern = re.compile(
        r"<!-- formula_id:\s*(\S+)\s*\|.*?-->\s*"
        r"(?:```latex\s*\n(.*?)\n```|<!-- No formula content.*?-->|\{\{FORMULA:.*?\}\})?",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        fid = match.group(1)
        latex = match.group(2).strip() if match.group(2) else ""
        formulas[fid] = latex

    return formulas


def generate_paper_html(
    paper_name: str,
    paper_info: dict,
    slots: list,
    canonical_formulas: dict[str, str],
    pdf_path: Path,
    output_dir: Path,
) -> list[dict]:
    """Generate HTML audit page for one paper. Returns audit rows."""
    overlays_dir = output_dir / "formula_overlays"
    crops_dir = output_dir / "formula_crops"
    canonical_path = output_dir / "canonical_paper.md"

    # Relative paths from visual_audit/ to paper dir
    paper_rel = f"../{paper_name}"

    rows = []
    for slot in slots:
        fid = slot["formula_id"]
        page = slot["page"]
        bbox = slot.get("bbox", [])
        section = slot.get("section", "")
        section_conf = slot.get("section_confidence", "low")
        section_source = slot.get("section_source", "unknown")
        section_reason = slot.get("section_reason", "")
        nearby_before = slot.get("nearby_text_before", "")
        nearby_after = slot.get("nearby_text_after", "")
        marker_latex = slot.get("marker_latex", "")
        final_latex = slot.get("final_latex", "")
        final_origin = slot.get("final_origin", "unresolved")
        crop_path = slot.get("crop_path", "")
        ocr_status = slot.get("ocr_status", "")

        # Check overlay exists
        overlay_path = f"{paper_rel}/formula_overlays/overlay_page{page}.png"
        overlay_full = output_dir / "formula_overlays" / f"overlay_page{page}.png"
        overlay_exists = overlay_full.exists()

        # Check crop exists
        crop_full = crops_dir / crop_path if crop_path else None
        crop_exists = crop_full.exists() if crop_full else False
        crop_rel = f"{paper_rel}/formula_crops/{crop_path}" if crop_path else ""

        # Check canonical match
        canonical_latex = canonical_formulas.get(fid, "")
        canonical_match = fid in canonical_formulas

        # Escape HTML
        def esc(s):
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        nearby_before_esc = esc(nearby_before[:500]) if nearby_before else "(empty)"
        nearby_after_esc = esc(nearby_after[:500]) if nearby_after else "(empty)"
        marker_latex_esc = esc(marker_latex) if marker_latex else "(none)"
        final_latex_esc = esc(final_latex) if final_latex else "(none)"
        canonical_latex_esc = esc(canonical_latex) if canonical_latex else "(not found in canonical)"
        section_reason_esc = esc(section_reason)

        rows.append({
            "formula_id": fid,
            "page": page,
            "bbox": bbox,
            "section": section,
            "section_confidence": section_conf,
            "section_source": section_source,
            "section_reason_esc": section_reason_esc,
            "nearby_before_esc": nearby_before_esc,
            "nearby_after_esc": nearby_after_esc,
            "marker_latex_esc": marker_latex_esc,
            "final_latex_esc": final_latex_esc,
            "final_origin": final_origin,
            "crop_rel": crop_rel,
            "crop_exists": crop_exists,
            "overlay_rel": overlay_path if overlay_exists else "",
            "overlay_exists": overlay_exists,
            "canonical_match": canonical_match,
            "canonical_latex_esc": canonical_latex_esc,
            "ocr_status": ocr_status,
        })

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M1 Visual Audit — {paper_name} ({paper_info['pid']})</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #fafafa; }}
  h1 {{ color: #333; border-bottom: 2px solid #4a90d9; padding-bottom: 8px; }}
  h2 {{ color: #555; margin-top: 30px; }}
  .stats {{ background: #e8f4fd; padding: 12px 16px; border-radius: 6px; margin: 16px 0; }}
  .formula-card {{
    background: white; border: 1px solid #ddd; border-radius: 8px;
    padding: 16px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}
  .formula-card h3 {{ margin: 0 0 8px 0; color: #2c5aa0; }}
  .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0; font-size: 14px; }}
  .meta dt {{ font-weight: bold; color: #666; }}
  .meta dd {{ margin: 0; }}
  .images {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0; }}
  .images img {{ max-height: 300px; border: 1px solid #ccc; border-radius: 4px; }}
  .images .caption {{ font-size: 12px; color: #888; text-align: center; }}
  pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 13px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: bold; }}
  .badge-ok {{ background: #d4edda; color: #155724; }}
  .badge-missing {{ background: #f8d7da; color: #721c24; }}
  .badge-warn {{ background: #fff3cd; color: #856404; }}
  .text-box {{ background: #f8f9fa; border-left: 3px solid #4a90d9; padding: 8px 12px; margin: 8px 0; font-size: 13px; max-height: 120px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; }}
</style>
</head>
<body>
<h1>M1 Visual Audit — {paper_name}</h1>
<div class="stats">
  <strong>Paper:</strong> {paper_info['title']} ({paper_info['pid']})<br>
  <strong>Total FormulaSlots:</strong> {len(rows)}<br>
  <strong>Overlays:</strong> {sum(1 for r in rows if r['overlay_exists'])}/{len(rows)} |
  <strong>Crops:</strong> {sum(1 for r in rows if r['crop_exists'])}/{len(rows)} |
  <strong>Canonical match:</strong> {sum(1 for r in rows if r['canonical_match'])}/{len(rows)}
</div>
<a href="index.html">← Back to Index</a>
"""

    for r in rows:
        origin_badge = "badge-ok" if r["final_origin"] == "parser_latex" else "badge-warn"
        overlay_badge = "badge-ok" if r["overlay_exists"] else "badge-missing"
        crop_badge = "badge-ok" if r["crop_exists"] else "badge-missing"
        canonical_badge = "badge-ok" if r["canonical_match"] else "badge-missing"

        html += f"""
<div class="formula-card" id="{r['formula_id']}">
  <h3>{r['formula_id']} <span class="badge {origin_badge}">{r['final_origin']}</span></h3>
  <dl class="meta">
    <dt>Paper</dt><dd>{paper_info['pid']}</dd>
    <dt>Page</dt><dd>{r['page']}</dd>
    <dt>Bbox</dt><dd>{r['bbox']}</dd>
    <dt>Section</dt><dd>{r['section']} <span class="badge badge-ok">{r['section_confidence']}</span></dd>
    <dt>Section Source</dt><dd>{r['section_source']}</dd>
    <dt>Section Reason</dt><dd>{r['section_reason_esc']}</dd>
    <dt>Origin</dt><dd>{r['final_origin']}</dd>
    <dt>OCR Status</dt><dd>{r['ocr_status']}</dd>
    <dt>Overlay</dt><dd><span class="badge {overlay_badge}">{'EXISTS' if r['overlay_exists'] else 'MISSING'}</span></dd>
    <dt>Crop</dt><dd><span class="badge {crop_badge}">{'EXISTS' if r['crop_exists'] else 'MISSING'}</span> {r['crop_rel']}</dd>
    <dt>Canonical Match</dt><dd><span class="badge {canonical_badge}">{'YES' if r['canonical_match'] else 'NO'}</span></dd>
  </dl>

  <h4>Nearby Text Before</h4>
  <div class="text-box">{r['nearby_before_esc']}</div>

  <h4>Nearby Text After</h4>
  <div class="text-box">{r['nearby_after_esc']}</div>

  <div class="images">
    <div>
      <div><strong>Overlay (page {r['page']})</strong></div>
      {"<img src='" + r['overlay_rel'] + "' alt='overlay' />" if r['overlay_exists'] else '<div class="badge badge-missing">NO OVERLAY</div>'}
      <div class="caption">Red bbox on page image</div>
    </div>
    <div>
      <div><strong>Crop</strong></div>
      {"<img src='" + r['crop_rel'] + "' alt='crop' />" if r['crop_exists'] else '<div class="badge badge-missing">NO CROP</div>'}
      <div class="caption">Cropped formula image</div>
    </div>
  </div>

  <h4>Marker LaTeX</h4>
  <pre>{r['marker_latex_esc']}</pre>

  <h4>Final LaTeX</h4>
  <pre>{r['final_latex_esc']}</pre>

  <h4>Canonical Comment</h4>
  <pre>{r['canonical_latex_esc']}</pre>
</div>
"""

    html += """
</body>
</html>
"""
    return html, rows


def main():
    import fitz

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    paper_stats = {}

    for paper_name, paper_info in PAPERS.items():
        print(f"\n{'=' * 60}")
        print(f"Processing {paper_name}")
        print(f"{'=' * 60}")

        pdf_path = ROOT / "reports" / "m1_parser_review" / paper_name / "source.pdf"
        output_dir = OUTPUT_DIR / paper_name
        overlays_dir = output_dir / "formula_overlays"
        canonical_path = output_dir / "canonical_paper.md"

        # Load formula slots
        slots_path = output_dir / "formula_slots.json"
        with open(slots_path, "r", encoding="utf-8") as f:
            slots = json.load(f)
        print(f"  {len(slots)} formula slots loaded")

        # Ensure ALL overlays exist
        print(f"  Ensuring overlays for all pages...")
        ensure_overlays(paper_name, slots, pdf_path, overlays_dir)

        # Extract canonical formulas
        canonical_formulas = extract_canonical_formulas(canonical_path)
        print(f"  {len(canonical_formulas)} formula comments in canonical")

        # Generate HTML
        html, rows = generate_paper_html(
            paper_name, paper_info, slots, canonical_formulas, pdf_path, output_dir
        )
        html_path = AUDIT_DIR / f"{paper_name}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  Wrote {html_path.name} ({len(rows)} formulas)")

        # Stats
        overlay_ok = sum(1 for r in rows if r["overlay_exists"])
        crop_ok = sum(1 for r in rows if r["crop_exists"])
        canonical_ok = sum(1 for r in rows if r["canonical_match"])
        paper_stats[paper_name] = {
            "total": len(rows),
            "overlay": overlay_ok,
            "crop": crop_ok,
            "canonical": canonical_ok,
            "title": paper_info["title"],
            "pid": paper_info["pid"],
        }
        for r in rows:
            r["paper"] = paper_name
            all_rows.append(r)

    # Generate SUMMARY.md
    summary_lines = [
        "# M1 Visual Audit — Summary",
        "",
        f"**Date**: 2026-06-09",
        f"**Total FormulaSlots**: {len(all_rows)}",
        "",
        "## Per-Paper Stats",
        "",
        "| Paper | Total | Overlays | Crops | Canonical |",
        "|-------|-------|----------|-------|-----------|",
    ]
    for pname, ps in paper_stats.items():
        summary_lines.append(
            f"| {pname} ({ps['pid']}) | {ps['total']} | {ps['overlay']}/{ps['total']} | {ps['crop']}/{ps['total']} | {ps['canonical']}/{ps['total']} |"
        )
    summary_lines.extend([
        "",
        "## Full Table",
        "",
        "| paper | formula_id | page | section | overlay_exists | crop_exists | latex_exists | canonical_match | needs_manual_check |",
        "|-------|-----------|-----:|---------|---------------|-------------|-------------|-----------------|-------------------|",
    ])
    for r in all_rows:
        overlay_e = "YES" if r["overlay_exists"] else "NO"
        crop_e = "YES" if r["crop_exists"] else "NO"
        latex_e = "YES" if r["final_latex_esc"] != "(none)" else "NO"
        canonical_m = "YES" if r["canonical_match"] else "NO"
        summary_lines.append(
            f"| {r['paper']} | {r['formula_id']} | {r['page']} | {r['section']} | {overlay_e} | {crop_e} | {latex_e} | {canonical_m} | YES |"
        )

    summary_path = AUDIT_DIR / "SUMMARY.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\nWrote {summary_path}")

    # Generate index.html
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M1 Visual Audit — Index</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #fafafa; }
  h1 { color: #333; }
  .card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .card h2 { margin: 0 0 8px 0; }
  .stats { display: flex; gap: 24px; margin: 8px 0; }
  .stat { text-align: center; }
  .stat .num { font-size: 28px; font-weight: bold; color: #2c5aa0; }
  .stat .label { font-size: 12px; color: #888; }
  a { color: #4a90d9; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>M1 Visual Audit</h1>
<p>Generated 2026-06-09. Total: """ + str(len(all_rows)) + """ FormulaSlots across 3 papers.</p>
"""

    for pname, ps in paper_stats.items():
        index_html += f"""
<div class="card">
  <h2><a href="{pname}.html">{pname}</a> — {ps['title']}</h2>
  <p>Paper ID: {ps['pid']}</p>
  <div class="stats">
    <div class="stat"><div class="num">{ps['total']}</div><div class="label">Formulas</div></div>
    <div class="stat"><div class="num">{ps['overlay']}</div><div class="label">Overlays</div></div>
    <div class="stat"><div class="num">{ps['crop']}</div><div class="label">Crops</div></div>
    <div class="stat"><div class="num">{ps['canonical']}</div><div class="label">Canonical</div></div>
  </div>
</div>
"""

    index_html += """
<h2>Links</h2>
<ul>
  <li><a href="SUMMARY.md">SUMMARY.md</a> — Full table</li>
</ul>
</body>
</html>
"""
    index_path = AUDIT_DIR / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"Wrote {index_path}")

    # Print final summary
    print(f"\n{'=' * 60}")
    print("VISUAL AUDIT COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total FormulaSlots: {len(all_rows)}")
    print(f"overlay_exists: {sum(1 for r in all_rows if r['overlay_exists'])}/{len(all_rows)}")
    print(f"crop_exists: {sum(1 for r in all_rows if r['crop_exists'])}/{len(all_rows)}")
    print(f"latex_exists: {sum(1 for r in all_rows if r['final_latex_esc'] != '(none)')}/{len(all_rows)}")
    print(f"canonical_match: {sum(1 for r in all_rows if r['canonical_match'])}/{len(all_rows)}")


if __name__ == "__main__":
    main()
