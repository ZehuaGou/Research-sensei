"""Generate VISUAL_AUDIT_CONTACT_SHEET.html for paper_4_unseen."""
import base64
import json
import re
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent
OUT_PATH = PAPER_DIR / "VISUAL_AUDIT_CONTACT_SHEET.html"


def img_to_base64(path):
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def extract_canonical(canonical_path):
    if not canonical_path.exists():
        return {}
    content = canonical_path.read_text(encoding="utf-8")
    formulas = {}
    pattern = re.compile(
        r"<!-- formula_id:\s*(\S+)\s*\|.*?-->\s*(?:```latex\s*\n(.*?)\n```|<!-- No formula content.*?-->|\{\{FORMULA:.*?\}\})?",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        fid = match.group(1)
        latex = match.group(2).strip() if match.group(2) else ""
        formulas[fid] = latex
    return formulas


def main():
    slots_path = PAPER_DIR / "formula_slots.json"
    with open(slots_path, "r", encoding="utf-8") as f:
        slots = json.load(f)

    canonical = extract_canonical(PAPER_DIR / "canonical_paper.md")
    crops_dir = PAPER_DIR / "formula_crops"
    overlays_dir = PAPER_DIR / "formula_overlays"

    rows = []
    for slot in slots:
        fid = slot["formula_id"]
        page = slot["page"]
        bbox = slot.get("bbox", [])
        section = slot.get("section", "Unknown")
        nearby_before = (slot.get("nearby_text_before") or "")[:120]
        nearby_after = (slot.get("nearby_text_after") or "")[:120]
        marker_latex = slot.get("marker_latex", "")
        final_latex = slot.get("final_latex", "")
        canonical_latex = canonical.get(fid, "")

        crop_path = crops_dir / slot.get("crop_path", "") if slot.get("crop_path") else None
        overlay_path = overlays_dir / ("overlay_page%d.png" % page)

        crop_b64 = img_to_base64(crop_path) if crop_path and crop_path.exists() else ""
        overlay_b64 = img_to_base64(overlay_path) if overlay_path.exists() else ""

        risk = "NONE" if section and section not in ("Unknown", "") else "LOW"
        risk_class = "risk-" + risk.lower()

        bbox_str = ", ".join("%.0f" % b for b in bbox)
        crop_html = "<img src='%s' alt='crop'>" % crop_b64 if crop_b64 else "<div style='width:150px;height:50px;background:#333;border-radius:4px'></div>"
        overlay_html = "<img src='%s' alt='overlay'>" % overlay_b64 if overlay_b64 else "<div style='width:300px;height:200px;background:#333;border-radius:4px'></div>"

        rows.append({
            "fid": fid, "page": page, "bbox_str": bbox_str, "section": section,
            "risk": risk, "risk_class": risk_class,
            "crop_html": crop_html, "overlay_html": overlay_html,
            "marker_latex": marker_latex[:300], "final_latex": final_latex[:300],
            "canonical_latex": canonical_latex[:300] if canonical_latex else "(not found)",
            "nearby_before": nearby_before, "nearby_after": nearby_after,
        })

    # Stats
    total = len(slots)
    crop_count = sum(1 for s in slots if s.get("crop_path") and (crops_dir / s["crop_path"]).exists())
    overlay_pages = set()
    for s in slots:
        p = s["page"]
        if (overlays_dir / ("overlay_page%d.png" % p)).exists():
            overlay_pages.add(p)
    overlay_count = sum(1 for s in slots if s["page"] in overlay_pages)
    section_count = sum(1 for s in slots if s.get("section") and s.get("section") not in ("Unknown", ""))

    # Build HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<title>M1 Contact Sheet - paper_4_unseen (MEMTO)</title>",
        "<style>",
        "* { box-sizing: border-box; margin: 0; padding: 0; }",
        "body { font-family: 'SF Mono', 'Consolas', monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }",
        "h1 { text-align: center; margin-bottom: 8px; color: #00d4ff; font-size: 20px; }",
        ".subtitle { text-align: center; color: #888; margin-bottom: 24px; font-size: 13px; }",
        ".formula-row {",
        "    display: grid; grid-template-columns: 200px 1fr 300px;",
        "    gap: 16px; background: #16213e; border: 1px solid #333;",
        "    border-radius: 8px; padding: 16px; margin-bottom: 16px; align-items: start;",
        "}",
        ".formula-id { font-weight: bold; color: #00d4ff; font-size: 16px; }",
        ".formula-meta { color: #888; font-size: 12px; margin-top: 4px; }",
        ".images { display: flex; gap: 12px; }",
        ".images img { max-height: 200px; border: 1px solid #444; border-radius: 4px; background: #fff; }",
        ".cap { font-size: 11px; color: #666; text-align: center; margin-top: 2px; }",
        ".latex-block { background: #0f3460; padding: 10px; border-radius: 4px; font-size: 12px; overflow-x: auto; margin-top: 8px; }",
        ".latex-label { color: #e94560; font-weight: bold; font-size: 11px; margin-bottom: 4px; }",
        ".nearby { color: #aaa; font-size: 11px; margin-top: 6px; font-style: italic; }",
        ".section-tag { display: inline-block; background: #533483; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-top: 4px; }",
        ".risk-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; }",
        ".risk-none { background: #28a745; color: #fff; }",
        ".risk-low { background: #ffc107; color: #000; }",
        ".summary { text-align: center; margin-top: 24px; color: #888; font-size: 13px; }",
        "</style></head><body>",
        "<h1>M1 Visual Audit Contact Sheet</h1>",
        "<div class='subtitle'>paper_4_unseen - MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection (arXiv 2312.02530)</div>",
    ]

    for r in rows:
        html_parts.append("<div class='formula-row'>")
        html_parts.append("<div>")
        html_parts.append("<div class='formula-id'>%s</div>" % r["fid"])
        html_parts.append("<div class='formula-meta'>Page %d</div>" % r["page"])
        html_parts.append("<div class='formula-meta'>BBox: [%s]</div>" % r["bbox_str"])
        html_parts.append("<div class='section-tag'>%s</div>" % r["section"][:30])
        html_parts.append("<div style='margin-top:6px'><span class='risk-badge %s'>%s</span></div>" % (r["risk_class"], r["risk"]))
        html_parts.append("</div>")
        html_parts.append("<div class='images'>")
        html_parts.append("<div>%s<div class='cap'>Crop</div></div>" % r["crop_html"])
        html_parts.append("<div>%s<div class='cap'>Overlay (page %d)</div></div>" % (r["overlay_html"], r["page"]))
        html_parts.append("</div>")
        html_parts.append("<div>")
        html_parts.append("<div class='latex-label'>Marker LaTeX:</div>")
        html_parts.append("<div class='latex-block'>%s</div>" % r["marker_latex"])
        html_parts.append("<div class='latex-label' style='margin-top:8px'>Final LaTeX:</div>")
        html_parts.append("<div class='latex-block'>%s</div>" % r["final_latex"])
        html_parts.append("<div class='latex-label' style='margin-top:8px'>Canonical LaTeX:</div>")
        html_parts.append("<div class='latex-block'>%s</div>" % r["canonical_latex"])
        html_parts.append("<div class='nearby'><strong>Before:</strong> %s</div>" % r["nearby_before"])
        html_parts.append("<div class='nearby'><strong>After:</strong> %s</div>" % r["nearby_after"])
        html_parts.append("</div>")
        html_parts.append("</div>")

    html_parts.append("<div class='summary'>")
    html_parts.append("Total: %d formulas | Crop: %d/%d | Overlay: %d/%d | Sections: %d/%d" % (
        total, crop_count, total, overlay_count, total, section_count, total))
    html_parts.append("</div>")
    html_parts.append("</body></html>")

    OUT_PATH.write_text("\n".join(html_parts), encoding="utf-8")
    print("Wrote %s (%d bytes)" % (OUT_PATH, OUT_PATH.stat().st_size))


if __name__ == "__main__":
    main()
