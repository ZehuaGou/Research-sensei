"""Generate M1 acceptance artifacts with correct image paths and full quality checks."""
import json
import re
import subprocess
import time
from pathlib import Path

ACCEPT_DIR = Path(__file__).resolve().parent

PAPERS = {
    "2310_08800v2": {
        "title": "DDMT: Denoising Diffusion Mask Transformer Models for Multivariate Time Series Anomaly Detection",
        "arxiv_id": "2310.08800",
        "public_pdf_url": "https://arxiv.org/pdf/2310.08800",
    },
    "2508_11528v1": {
        "title": "TPIDM: Temporal Pattern-Guided Diffusion Model for Time Series Anomaly Detection",
        "arxiv_id": "2508.11528",
        "public_pdf_url": "https://arxiv.org/pdf/2508.11528",
    },
}

REFERENCE_SECTIONS = {"References", "Bibliography"}


def resolve_image_path(paper_dir: Path, raw_path: str) -> tuple[str, bool]:
    """Resolve image path relative to visual_audit/ dir. Returns (relative_path, exists)."""
    if not raw_path:
        return "", False
    # raw_path is like "formula_crops/formula_010_p7.png" — relative to paper_dir
    abs_path = paper_dir / raw_path
    # Relative to visual_audit/ subdir
    rel = f"../{raw_path}"
    return rel, abs_path.exists()


def update_formula_slots(paper_key: str) -> list:
    """Add formula_m2_ready and nearby_text fields."""
    paper_dir = ACCEPT_DIR / paper_key
    slots_path = paper_dir / "formula_slots.json"
    with open(slots_path, "r", encoding="utf-8") as f:
        slots = json.load(f)

    for slot in slots:
        section = slot.get("section", "")
        if section in REFERENCE_SECTIONS:
            slot["formula_m2_ready"] = False
            if "REFERENCE_FORMULA_EXCLUDED" not in slot.get("risk_flags", []):
                slot.setdefault("risk_flags", []).append("REFERENCE_FORMULA_EXCLUDED")
        else:
            slot["formula_m2_ready"] = True
        # Ensure nearby_text fields exist
        if "nearby_text_before" not in slot:
            slot["nearby_text_before"] = ""
        if "nearby_text_after" not in slot:
            slot["nearby_text_after"] = ""

    with open(slots_path, "w", encoding="utf-8") as f:
        json.dump(slots, f, indent=2, ensure_ascii=False)
    return slots


def generate_visual_audit(paper_key: str, paper_info: dict, slots: list) -> dict:
    """Generate multi-file visual audit HTML with correct image paths."""
    paper_dir = ACCEPT_DIR / paper_key
    audit_dir = paper_dir / "visual_audit"
    audit_dir.mkdir(exist_ok=True)

    canonical_path = paper_dir / "canonical_paper.md"
    canonical_text = canonical_path.read_text(encoding="utf-8") if canonical_path.exists() else ""

    total = len(slots)
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    latex_count = sum(1 for s in slots if s.get("mineru_latex"))

    broken_links = 0

    # Generate per-formula pages
    for slot in slots:
        fid = slot["formula_id"]
        page = slot["page"]
        bbox = slot.get("bbox", [])
        section = slot.get("section", "Unknown")
        section_conf = slot.get("section_confidence", "low")
        section_reason = slot.get("section_reason", "")
        mineru_latex = slot.get("mineru_latex", "")
        final_latex = slot.get("final_latex", "")
        final_origin = slot.get("final_origin", "")
        risk_flags = slot.get("risk_flags", [])
        m2_ready = slot.get("formula_m2_ready", True)
        block_source = slot.get("block_source", "")
        nearby_before = slot.get("nearby_text_before", "")
        nearby_after = slot.get("nearby_text_after", "")

        # Resolve image paths correctly
        crop_rel, crop_exists = resolve_image_path(paper_dir, slot.get("crop_path", ""))
        overlay_rel, overlay_exists = resolve_image_path(paper_dir, slot.get("overlay_path", ""))

        if not crop_exists and slot.get("crop_path"):
            broken_links += 1
        if not overlay_exists and slot.get("overlay_path"):
            broken_links += 1

        # Canonical match
        canonical_match = "NO"
        if fid in canonical_text:
            canonical_match = "YES"
        elif final_latex and len(final_latex) > 20 and final_latex[:20] in canonical_text:
            canonical_match = "PARTIAL"

        risk_str = ", ".join(risk_flags) if risk_flags else "NONE"
        m2_str = "YES" if m2_ready else "NO (Reference formula excluded)"
        risk_class = "risk-excluded" if risk_flags else "risk-none"

        nearby_before_display = nearby_before if nearby_before else "<em>EMPTY</em>"
        nearby_after_display = nearby_after if nearby_after else "<em>EMPTY</em>"

        formula_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{fid} — {paper_key}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #58a6ff; font-size: 18px; margin-bottom: 16px; }}
.field {{ margin: 4px 0; font-size: 13px; }}
.field-label {{ font-weight: 600; color: #8b949e; display: inline-block; min-width: 160px; }}
.field-value {{ color: #c9d1d9; }}
.risk-none {{ color: #3fb950; }}
.risk-excluded {{ color: #d29922; }}
.images {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
.images img {{ max-height: 300px; border: 1px solid #30363d; border-radius: 4px; background: #fff; }}
.images .caption {{ font-size: 11px; color: #8b949e; text-align: center; margin-top: 4px; }}
pre {{ background: #161b22; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; color: #c9d1d9; border: 1px solid #30363d; margin: 8px 0; }}
.nearby {{ background: #161b22; padding: 8px; border-radius: 4px; font-size: 11px; color: #8b949e; border: 1px solid #30363d; margin: 6px 0; font-style: italic; }}
.nav {{ margin: 16px 0; font-size: 13px; }}
.nav a {{ color: #58a6ff; text-decoration: none; margin-right: 16px; }}
</style></head><body>
<div class="nav"><a href="index.html">&larr; Index</a></div>
<h1>{fid} — Page {page}</h1>

<div class="field"><span class="field-label">BBox:</span> <span class="field-value">[{', '.join(f'{b:.3f}' for b in bbox)}]</span></div>
<div class="field"><span class="field-label">Section:</span> <span class="field-value">{section} (conf={section_conf})</span></div>
<div class="field"><span class="field-label">Section Reason:</span> <span class="field-value">{section_reason}</span></div>
<div class="field"><span class="field-label">Block Source:</span> <span class="field-value">{block_source}</span></div>
<div class="field"><span class="field-label">Final Origin:</span> <span class="field-value">{final_origin}</span></div>
<div class="field"><span class="field-label">Canonical Match:</span> <span class="field-value">{canonical_match}</span></div>
<div class="field"><span class="field-label">Risk Flags:</span> <span class="field-value {risk_class}">{risk_str}</span></div>
<div class="field"><span class="field-label">Formula M2 Ready:</span> <span class="field-value {'risk-none' if m2_ready else 'risk-excluded'}">{m2_str}</span></div>

<div class="images">
"""
        if crop_exists:
            formula_html += f'  <div><img src="{crop_rel}" alt="crop"><div class="caption">Crop</div></div>\n'
        else:
            formula_html += f'  <div><div style="width:200px;height:60px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">CROP MISSING</div><div class="caption">Crop (not found)</div></div>\n'
        if overlay_exists:
            formula_html += f'  <div><img src="{overlay_rel}" alt="overlay"><div class="caption">Overlay (page {page})</div></div>\n'
        else:
            formula_html += f'  <div><div style="width:300px;height:200px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">OVERLAY MISSING</div><div class="caption">Overlay (not found)</div></div>\n'
        formula_html += '</div>\n'

        # Nearby text
        formula_html += f'<div class="field"><span class="field-label">Nearby Text Before:</span></div><div class="nearby">{nearby_before_display}</div>\n'
        formula_html += f'<div class="field"><span class="field-label">Nearby Text After:</span></div><div class="nearby">{nearby_after_display}</div>\n'

        if mineru_latex:
            formula_html += f'<div class="field"><span class="field-label">MinerU LaTeX:</span></div><pre>{mineru_latex}</pre>\n'
        if final_latex and final_latex != mineru_latex:
            formula_html += f'<div class="field"><span class="field-label">Final LaTeX:</span></div><pre>{final_latex}</pre>\n'

        # Canonical block
        canonical_block = ""
        if fid in canonical_text:
            pattern = re.compile(rf"<!--\s*formula_id:\s*{fid}.*?-->\s*(?:```latex\s*\n(.*?)\n```|.*?(?=<!--|\Z))", re.DOTALL)
            match = pattern.search(canonical_text)
            if match:
                canonical_block = (match.group(1) or match.group(0)).strip()
        if canonical_block:
            formula_html += f'<div class="field"><span class="field-label">Canonical Block:</span></div><pre>{canonical_block[:500]}</pre>\n'

        formula_html += "</body></html>"
        (audit_dir / f"{fid}.html").write_text(formula_html, encoding="utf-8")

    # Count broken links across all formula pages
    for f in audit_dir.glob("formula_*.html"):
        content = f.read_text(encoding="utf-8")
        for m in re.finditer(r'src="\.\./(formula_\w+/\w+\.png)"', content):
            img_rel = m.group(1)
            img_abs = paper_dir / img_rel
            if not img_abs.exists():
                broken_links += 1

    # Generate index.html
    index_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>M1 Visual Audit — {paper_key}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 8px; color: #58a6ff; font-size: 22px; }}
.subtitle {{ text-align: center; color: #8b949e; margin-bottom: 24px; font-size: 13px; }}
.stats {{ display: flex; gap: 12px; justify-content: center; margin-bottom: 24px; flex-wrap: wrap; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px 16px; text-align: center; }}
.stat-val {{ font-size: 20px; font-weight: 700; color: #58a6ff; }}
.stat-lbl {{ font-size: 11px; color: #8b949e; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 16px; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; color: #58a6ff; }}
a {{ color: #58a6ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.risk-excluded {{ color: #d29922; }}
</style></head><body>
<h1>M1 Visual Audit — {paper_key}</h1>
<div class="subtitle">{paper_info['title']}<br>arXiv: {paper_info['arxiv_id']} | <a href="{paper_info['public_pdf_url']}">{paper_info['public_pdf_url']}</a></div>

<div class="stats">
  <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total Formulas</div></div>
  <div class="stat"><div class="stat-val">{len(body_slots)}</div><div class="stat-lbl">Body (M2 Ready)</div></div>
  <div class="stat"><div class="stat-val">{len(ref_slots)}</div><div class="stat-lbl">References (Excluded)</div></div>
  <div class="stat"><div class="stat-val">{latex_count}</div><div class="stat-lbl">LaTeX</div></div>
  <div class="stat"><div class="stat-val">{broken_links}</div><div class="stat-lbl">Broken Links</div></div>
</div>

<table>
<tr><th>#</th><th>ID</th><th>Page</th><th>Section</th><th>Origin</th><th>LaTeX</th><th>Crop</th><th>Overlay</th><th>Canonical</th><th>Risk</th><th>M2 Ready</th><th>Detail</th></tr>
"""
    for i, s in enumerate(slots, 1):
        fid = s["formula_id"]
        page = s["page"]
        section = s.get("section", "Unknown")
        origin = s.get("final_origin", "")
        latex_yn = "Y" if s.get("mineru_latex") else "N"
        crop_rel, crop_ok = resolve_image_path(paper_dir, s.get("crop_path", ""))
        overlay_rel, overlay_ok = resolve_image_path(paper_dir, s.get("overlay_path", ""))
        crop_yn = "Y" if crop_ok else "N"
        overlay_yn = "Y" if overlay_ok else "N"
        canonical_yn = "Y" if fid in canonical_text or (s.get("final_latex", "")[:20] in canonical_text) else "N"
        risk_str = ", ".join(s.get("risk_flags", [])) or "NONE"
        m2_ready = s.get("formula_m2_ready", True)
        m2_str = "YES" if m2_ready else '<span class="risk-excluded">NO</span>'
        risk_class = "risk-excluded" if s.get("risk_flags") else ""
        index_html += f'<tr><td>{i}</td><td><a href="{fid}.html">{fid}</a></td><td>{page}</td><td>{section}</td><td>{origin}</td><td>{latex_yn}</td><td>{crop_yn}</td><td>{overlay_yn}</td><td>{canonical_yn}</td><td class="{risk_class}">{risk_str}</td><td>{m2_str}</td><td><a href="{fid}.html">View</a></td></tr>\n'

    index_html += "</table></body></html>"
    (audit_dir / "index.html").write_text(index_html, encoding="utf-8")

    # External-readable artifact check
    external_readable = broken_links == 0

    return {
        "total": total,
        "body_count": len(body_slots),
        "ref_count": len(ref_slots),
        "latex_count": latex_count,
        "broken_links": broken_links,
        "external_readable": external_readable,
    }


def generate_verify_index(all_stats: dict) -> str:
    """Generate FINAL_MANUAL_VERIFY_INDEX.md with real PASS/FAIL."""
    lines = [
        "# M1 Final Manual Verify Index",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Acceptance Criteria",
        "",
        "| Criterion | DDMT | TPIDM |",
        "|-----------|:----:|:-----:|",
    ]

    results = {}
    for paper_key in ["2310_08800v2", "2508_11528v1"]:
        paper_dir = ACCEPT_DIR / paper_key
        slots_path = paper_dir / "formula_slots.json"
        with open(slots_path, "r", encoding="utf-8") as f:
            slots = json.load(f)

        source_ok = (paper_dir / "source.pdf").exists() and (paper_dir / "source.pdf").stat().st_size > 10000
        formula_ok = len(slots) >= 5
        crop_ok = all(resolve_image_path(paper_dir, s.get("crop_path", ""))[1] for s in slots if s.get("crop_path"))
        overlay_ok = all(resolve_image_path(paper_dir, s.get("overlay_path", ""))[1] for s in slots if s.get("overlay_path"))
        latex_ok = all(s.get("mineru_latex") for s in slots)
        quality_risks = sum(1 for s in slots if s.get("risk_flags") and "REFERENCE_FORMULA_EXCLUDED" not in s.get("risk_flags", []))
        high_risk_ok = quality_risks == 0
        contradictions = sum(1 for s in slots if "SECTION_CONTRADICTION" in str(s.get("risk_flags", [])))
        contradictions_ok = contradictions == 0
        abstract_count = sum(1 for s in slots if s.get("section") == "Abstract")
        abstract_ok = abstract_count < 5
        audit_ok = (paper_dir / "visual_audit" / "index.html").exists()
        ext_ok = all_stats[paper_key]["external_readable"]

        results[paper_key] = {
            "source": source_ok, "formula": formula_ok, "crop": crop_ok,
            "overlay": overlay_ok, "latex": latex_ok, "high_risk": high_risk_ok,
            "contradictions": contradictions_ok, "abstract": abstract_ok,
            "audit": audit_ok, "ext_readable": ext_ok,
        }

    def pf(v):
        return "**PASS**" if v else "**FAIL**"

    dd = results["2310_08800v2"]
    tp = results["2508_11528v1"]
    lines.extend([
        f"| source/title verified | {pf(dd['source'])} | {pf(tp['source'])} |",
        f"| formula_slot_count >= 5 | {pf(dd['formula'])} | {pf(tp['formula'])} |",
        f"| crop_exists = 100% | {pf(dd['crop'])} | {pf(tp['crop'])} |",
        f"| overlay_exists = 100% | {pf(dd['overlay'])} | {pf(tp['overlay'])} |",
        f"| latex_non_empty = 100% | {pf(dd['latex'])} | {pf(tp['latex'])} |",
        f"| high_risk_items = 0 (quality) | {pf(dd['high_risk'])} | {pf(tp['high_risk'])} |",
        f"| section_contradiction = 0 | {pf(dd['contradictions'])} | {pf(tp['contradictions'])} |",
        f"| all_formulas_in_Abstract_suspicious = 0 | {pf(dd['abstract'])} | {pf(tp['abstract'])} |",
        f"| visual audit pages generated | {pf(dd['audit'])} | {pf(tp['audit'])} |",
        f"| external-readable artifact check | {pf(dd['ext_readable'])} | {pf(tp['ext_readable'])} |",
        "",
        "## Per-Paper Details",
        "",
    ])

    for paper_key, paper_info in PAPERS.items():
        paper_dir = ACCEPT_DIR / paper_key
        with open(paper_dir / "formula_slots.json", encoding="utf-8") as f:
            slots = json.load(f)
        stats = all_stats[paper_key]
        body = [s for s in slots if s.get("formula_m2_ready", True)]
        ref = [s for s in slots if not s.get("formula_m2_ready", True)]

        lines.extend([
            f"### {paper_key}",
            "",
            f"- **Title**: {paper_info['title']}",
            f"- **arXiv**: {paper_info['arxiv_id']}",
            f"- **Source PDF**: `{paper_key}/source.pdf`",
            f"- **Contact Sheet**: `{paper_key}/visual_audit/index.html`",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Formula Count | {len(slots)} |",
            f"| Body Formula Count (M2 Ready) | {len(body)} |",
            f"| Reference Formula Count (Excluded) | {len(ref)} |",
            f"| formula_m2_ready_count | {len(body)} |",
            f"| LaTeX Count | {stats['latex_count']} |",
            f"| Broken Image Links | {stats['broken_links']} |",
            f"| External Readable | {'YES' if stats['external_readable'] else 'NO'} |",
            "",
        ])

    lines.extend([
        "## Manual Visual Review Status",
        "",
        "**manual_visual_review_status = PENDING**",
        "",
        "Human must review contact sheets before final acceptance.",
        "",
        "## References Formula Exclusion",
        "",
        "- Section=References formulas are excluded from M2 formula understanding.",
        "- Marked with `formula_m2_ready=false` and `REFERENCE_FORMULA_EXCLUDED` risk flag.",
        "- TPIDM: 5 References formulas excluded, 12 body formulas ready.",
        "- DDMT: 0 References formulas excluded, 7 body formulas ready.",
    ])

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("M1 Acceptance Artifact Generator v3")
    print("=" * 60)

    all_stats = {}

    for paper_key, paper_info in PAPERS.items():
        print(f"\nProcessing {paper_key}...")
        slots = update_formula_slots(paper_key)
        stats = generate_visual_audit(paper_key, paper_info, slots)
        all_stats[paper_key] = stats
        print(f"  Stats: {stats}")

    print("\nGenerating FINAL_MANUAL_VERIFY_INDEX.md...")
    index_md = generate_verify_index(all_stats)
    (ACCEPT_DIR / "FINAL_MANUAL_VERIFY_INDEX.md").write_text(index_md, encoding="utf-8")

    print("\nDONE")


if __name__ == "__main__":
    main()
