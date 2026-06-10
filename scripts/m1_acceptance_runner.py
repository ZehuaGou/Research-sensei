"""M1 Acceptance Runner — run full M1 pipeline on a searched paper and generate acceptance package.

Reads selected_paper_metadata.json from reports/m1_unseen_paper_search/, runs
MinerU2.5-Pro → RuleBasedStructureRefiner → CanonicalBuilder → M1QualityGate,
generates visual audit, and packages everything into a zip.
"""
from __future__ import annotations

import datetime
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "reports" / "m1_unseen_paper_search"


def main() -> int:
    print("=" * 60)
    print("M1 Acceptance Runner")
    print("=" * 60)

    # Load selected paper metadata
    meta_path = SEARCH_DIR / "selected_paper_metadata.json"
    if not meta_path.exists():
        print("ERROR: selected_paper_metadata.json not found. Run m1_unseen_paper_search.py first.")
        return 1

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    paper_id = meta["paper_id"]
    title = meta["title"]
    pdf_path = Path(meta["downloaded_pdf_path"])

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return 1

    print(f"Paper: {paper_id} - {title}")
    print(f"PDF: {pdf_path}")

    # Create acceptance directory
    accept_dir = ROOT / "reports" / f"m1_acceptance_manual_review_{paper_id}"
    accept_dir.mkdir(parents=True, exist_ok=True)

    # Copy source PDF
    source_pdf = accept_dir / "source.pdf"
    shutil.copy2(pdf_path, source_pdf)
    print(f"Copied source.pdf ({source_pdf.stat().st_size} bytes)")

    # Run M1 pipeline
    print("\n[1/6] Running MinerU2.5-Pro pipeline...")
    start = time.perf_counter()

    from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    adapter = MinerU25ProAdapter()
    pipeline = M1CanonicalPipeline(mineru_adapter=adapter)

    result = pipeline.run_pdf(
        paper_id=paper_id,
        title=title,
        pdf_path=source_pdf,
        output_dir=accept_dir,
        apply_ollama=False,
    )

    elapsed = time.perf_counter() - start
    print(f"  Pipeline completed in {elapsed:.1f}s")
    print(f"  Quality: {result.quality.status.value}")
    print(f"  M2 ready: {result.canonicalization.m2_ready}")
    print(f"  Formula slots: {len(result.formula_slots)}")
    print(f"  Blocks: {len(result.blocks)}")

    # Copy search artifacts
    print("\n[2/6] Copying search artifacts...")
    for name in [
        "search_config.json", "search_queries.json", "candidate_papers.json",
        "rejected_candidates.md", "selected_paper_metadata.json", "paper_search_report.md",
    ]:
        src = SEARCH_DIR / name
        if src.exists():
            shutil.copy2(src, accept_dir / name)
            print(f"  Copied {name}")

    # Write paper_metadata.json
    print("\n[3/6] Writing paper metadata...")
    paper_meta = {
        **meta,
        "pipeline_elapsed_seconds": round(elapsed, 3),
        "quality_status": result.quality.status.value,
        "m2_ready": result.canonicalization.m2_ready,
        "formula_slot_count": len(result.formula_slots),
        "block_count": len(result.blocks),
        "primary_parser": "mineru25pro",
        "ollama_enabled": False,
    }
    (accept_dir / "paper_metadata.json").write_text(
        json.dumps(paper_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Generate visual audit with per-formula pages
    print("\n[4/6] Generating visual audit...")
    generate_visual_audit(accept_dir, result)

    # Generate FINAL_MANUAL_VERIFY_INDEX.md
    print("\n[5/6] Generating verification index...")
    generate_verify_index(accept_dir, result, meta)

    # Generate compare report
    generate_compare_report(accept_dir, result)

    # Generate quality report
    generate_quality_report(accept_dir, result, meta)

    # Create zip
    print("\n[6/6] Creating zip package...")
    zip_path = ROOT / "reports" / f"m1_acceptance_manual_review_{paper_id}.zip"
    create_zip(accept_dir, zip_path)
    print(f"  Zip: {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")

    print(f"\nDONE. Acceptance package: {accept_dir}")
    return 0


def generate_visual_audit(accept_dir: Path, result) -> None:
    """Generate per-formula HTML pages and index."""
    audit_dir = accept_dir / "visual_audit"
    audit_dir.mkdir(exist_ok=True)

    canonical_path = accept_dir / "canonical_paper.md"
    canonical_text = canonical_path.read_text(encoding="utf-8") if canonical_path.exists() else ""

    slots = result.formula_slots
    total = len(slots)
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    latex_count = sum(1 for s in slots if s.get("final_latex"))

    # Per-formula pages
    for slot in slots:
        fid = slot["formula_id"]
        page = slot.get("page", 0)
        bbox = slot.get("bbox", [])
        section = slot.get("section", "Unknown")
        section_conf = slot.get("section_confidence", "low")
        section_reason = slot.get("section_reason", "")
        final_latex = slot.get("final_latex", "")
        final_origin = slot.get("final_origin", "")
        risk_flags = slot.get("risk_flags", [])
        m2_ready = slot.get("formula_m2_ready", True)
        block_source = slot.get("block_source", "")
        nearby_before = slot.get("nearby_text_before", "")
        nearby_after = slot.get("nearby_text_after", "")

        crop_path = slot.get("crop_path", "")
        overlay_path = slot.get("overlay_path", "")
        crop_exists = (accept_dir / crop_path).exists() if crop_path else False
        overlay_exists = (accept_dir / overlay_path).exists() if overlay_path else False

        risk_str = ", ".join(risk_flags) if risk_flags else "NONE"
        m2_str = "YES" if m2_ready else "NO (excluded)"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{fid} — {page}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #58a6ff; font-size: 18px; margin-bottom: 16px; }}
.field {{ margin: 4px 0; font-size: 13px; }}
.field-label {{ font-weight: 600; color: #8b949e; display: inline-block; min-width: 160px; }}
.images {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
.images img {{ max-height: 300px; border: 1px solid #30363d; border-radius: 4px; background: #fff; }}
.images .caption {{ font-size: 11px; color: #8b949e; text-align: center; margin-top: 4px; }}
pre {{ background: #161b22; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; border: 1px solid #30363d; margin: 8px 0; }}
.nearby {{ background: #161b22; padding: 8px; border-radius: 4px; font-size: 11px; color: #8b949e; border: 1px solid #30363d; margin: 6px 0; font-style: italic; }}
.risk-none {{ color: #3fb950; }}
.risk-excluded {{ color: #d29922; }}
.nav {{ margin: 16px 0; font-size: 13px; }}
.nav a {{ color: #58a6ff; text-decoration: none; margin-right: 16px; }}
</style></head><body>
<div class="nav"><a href="index.html">&larr; Index</a></div>
<h1>{fid} — Page {page}</h1>

<div class="field"><span class="field-label">Section:</span> {section} (conf={section_conf})</div>
<div class="field"><span class="field-label">Section Reason:</span> {section_reason}</div>
<div class="field"><span class="field-label">Block Source:</span> {block_source}</div>
<div class="field"><span class="field-label">Final Origin:</span> {final_origin}</div>
<div class="field"><span class="field-label">Risk Flags:</span> <span class="{'risk-excluded' if risk_flags else 'risk-none'}">{risk_str}</span></div>
<div class="field"><span class="field-label">Formula M2 Ready:</span> <span class="{'risk-none' if m2_ready else 'risk-excluded'}">{m2_str}</span></div>

<div class="images">
"""
        if crop_exists:
            html += f'  <div><img src="../{crop_path}" alt="crop"><div class="caption">Crop</div></div>\n'
        else:
            html += f'  <div><div style="width:200px;height:60px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">CROP MISSING</div><div class="caption">Crop</div></div>\n'
        if overlay_exists:
            html += f'  <div><img src="../{overlay_path}" alt="overlay"><div class="caption">Overlay (page {page})</div></div>\n'
        else:
            html += f'  <div><div style="width:300px;height:200px;background:#333;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#f85149;">OVERLAY MISSING</div><div class="caption">Overlay</div></div>\n'
        html += '</div>\n'

        before_display = nearby_before if nearby_before else "<em>EMPTY</em>"
        after_display = nearby_after if nearby_after else "<em>EMPTY</em>"
        html += f'<div class="field"><span class="field-label">Nearby Text Before:</span></div><div class="nearby">{before_display}</div>\n'
        html += f'<div class="field"><span class="field-label">Nearby Text After:</span></div><div class="nearby">{after_display}</div>\n'

        if final_latex:
            html += f'<div class="field"><span class="field-label">LaTeX:</span></div><pre>{final_latex}</pre>\n'

        html += "</body></html>"
        (audit_dir / f"{fid}.html").write_text(html, encoding="utf-8")

    # Index page
    index_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>M1 Visual Audit</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 8px; color: #58a6ff; font-size: 22px; }}
.stats {{ display: flex; gap: 12px; justify-content: center; margin-bottom: 24px; flex-wrap: wrap; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px 16px; text-align: center; }}
.stat-val {{ font-size: 20px; font-weight: 700; color: #58a6ff; }}
.stat-lbl {{ font-size: 11px; color: #8b949e; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; color: #58a6ff; }}
a {{ color: #58a6ff; text-decoration: none; }}
.risk-excluded {{ color: #d29922; }}
</style></head><body>
<h1>M1 Visual Audit</h1>
<div class="stats">
  <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total Formulas</div></div>
  <div class="stat"><div class="stat-val">{len(body_slots)}</div><div class="stat-lbl">Body (M2 Ready)</div></div>
  <div class="stat"><div class="stat-val">{len(ref_slots)}</div><div class="stat-lbl">References (Excluded)</div></div>
  <div class="stat"><div class="stat-val">{latex_count}</div><div class="stat-lbl">LaTeX</div></div>
</div>
<table>
<tr><th>#</th><th>ID</th><th>Page</th><th>Section</th><th>Origin</th><th>LaTeX</th><th>Risk</th><th>M2 Ready</th><th>Detail</th></tr>
"""
    for i, s in enumerate(slots, 1):
        fid = s["formula_id"]
        latex_yn = "Y" if s.get("final_latex") else "N"
        risk_str = ", ".join(s.get("risk_flags", [])) or "NONE"
        m2_ready = s.get("formula_m2_ready", True)
        m2_str = "YES" if m2_ready else '<span class="risk-excluded">NO</span>'
        risk_class = "risk-excluded" if s.get("risk_flags") else ""
        index_html += (
            f'<tr><td>{i}</td><td><a href="{fid}.html">{fid}</a></td>'
            f'<td>{s.get("page", 0)}</td><td>{s.get("section", "?")}</td>'
            f'<td>{s.get("final_origin", "")}</td><td>{latex_yn}</td>'
            f'<td class="{risk_class}">{risk_str}</td><td>{m2_str}</td>'
            f'<td><a href="{fid}.html">View</a></td></tr>\n'
        )
    index_html += "</table></body></html>"
    (audit_dir / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  Visual audit: {len(slots)} formula pages + index")


def generate_verify_index(accept_dir: Path, result, meta: dict) -> None:
    """Generate FINAL_MANUAL_VERIFY_INDEX.md."""
    slots = result.formula_slots
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    raw_only = [s for s in body_slots if s.get("final_origin") == "raw_formula_text"]
    dense_raw = [s for s in body_slots if not s.get("final_latex") and len(body_slots) >= 5]

    lines = [
        "# M1 Final Manual Verify Index",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Paper Information",
        "",
        f"- **Title**: {meta['title']}",
        f"- **arXiv ID**: {meta['arxiv_id']}",
        f"- **PDF URL**: {meta['pdf_url']}",
        f"- **Published**: {meta['published']}",
        f"- **Search Query**: `{meta['search_query_that_found_it']}`",
        "",
        "## Search Process",
        "",
        f"- Search date: {meta['timestamp']}",
        f"- Formula pre-screen count: {meta['formula_prescreen_count']}",
        f"- Selection reason: {meta['selected_reason']}",
        "",
        "## Pipeline Result",
        "",
        f"- Quality status: **{result.quality.status.value}**",
        f"- M2 ready: **{result.canonicalization.m2_ready}**",
        f"- Primary parser: MinerU2.5-Pro",
        f"- Ollama: disabled",
        "",
        "## Formula Summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Total formulas | {len(slots)} |",
        f"| Body formulas (M2 ready) | {len(body_slots)} |",
        f"| Reference formulas (excluded) | {len(ref_slots)} |",
        f"| Raw-only formulas | {len(raw_only)} |",
        f"| Formulas with LaTeX | {sum(1 for s in slots if s.get('final_latex'))} |",
        f"| Formulas with crop | {sum(1 for s in slots if s.get('crop_path'))} |",
        f"| Formulas with overlay | {sum(1 for s in slots if s.get('overlay_path'))} |",
        "",
        "## Per-Formula Verification",
        "",
        "| # | ID | Page | Section | Origin | LaTeX | Crop | Overlay | M2 Ready | Detail |",
        "|---|-----|------|---------|--------|:-----:|:----:|:-------:|:--------:|--------|",
    ]
    for i, s in enumerate(slots, 1):
        latex_yn = "Y" if s.get("final_latex") else "N"
        crop_yn = "Y" if s.get("crop_path") and (accept_dir / s["crop_path"]).exists() else "N"
        overlay_yn = "Y" if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists() else "N"
        m2_yn = "YES" if s.get("formula_m2_ready", True) else "NO"
        lines.append(
            f"| {i} | [{s['formula_id']}](visual_audit/{s['formula_id']}.html) "
            f"| {s.get('page', 0)} | {s.get('section', '?')} | {s.get('final_origin', '')} "
            f"| {latex_yn} | {crop_yn} | {overlay_yn} | {m2_yn} | [View](visual_audit/{s['formula_id']}.html) |"
        )

    lines += [
        "",
        "## Manual Verification Checklist",
        "",
        "Human must verify each formula:",
        "",
        "- [ ] PDF page matches formula location",
        "- [ ] Overlay red box correctly bounds the formula",
        "- [ ] Crop image shows the actual formula (not surrounding text)",
        "- [ ] LaTeX matches the visual formula in the crop",
        "- [ ] Section assignment is correct",
        "- [ ] canonical_paper.md correctly references the formula",
        "",
        "## Verification Status",
        "",
        "**manual_visual_verification_status = PENDING**",
        "",
        "Codex generates this acceptance package for human review. "
        "The user must upload the zip and verify each formula visually. "
        "Codex cannot claim manual verification passed.",
        "",
        "## Artifacts",
        "",
        "- source.pdf",
        "- canonical_paper.md",
        "- formula_slots.json / formula_slots.md",
        "- document_blocks.json",
        "- formula_crops/",
        "- formula_overlays/",
        "- visual_audit/index.html + per-formula HTML",
        "- paper_metadata.json",
        "- paper_search_report.md",
        "- candidate_papers.json",
        "- rejected_candidates.md",
        "- selected_paper_metadata.json",
        "- compare_report.md",
        "- quality_report.md",
    ]
    (accept_dir / "FINAL_MANUAL_VERIFY_INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  Verification index: {len(slots)} formulas listed")


def generate_compare_report(accept_dir: Path, result) -> None:
    """Generate compare report showing artifact traceability."""
    slots = result.formula_slots
    lines = [
        "# M1 Compare Report: Artifact Traceability",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Artifact Cross-Reference",
        "",
        "This report verifies that all M1 artifacts can be traced back to the source PDF.",
        "",
        "### source.pdf → document_blocks.json",
        "",
        f"- source.pdf exists: {(accept_dir / 'source.pdf').exists()}",
        f"- document_blocks.json exists: {(accept_dir / 'document_blocks.json').exists()}",
        f"- Blocks count: {len(result.blocks)}",
        f"- Blocks with page info: {sum(1 for b in result.blocks if b.page > 0)}",
        f"- Blocks with bbox: {sum(1 for b in result.blocks if b.bbox)}",
        "",
        "### document_blocks.json → formula_slots.json",
        "",
        f"- formula_slots.json exists: {(accept_dir / 'formula_slots.json').exists()}",
        f"- Formula slots: {len(slots)}",
        f"- Slots with block_id: {sum(1 for s in slots if s.get('block_id'))}",
        "",
        "### formula_slots.json → formula_crops/ / formula_overlays/",
        "",
    ]
    crop_ok = 0
    overlay_ok = 0
    for s in slots:
        if s.get("crop_path") and (accept_dir / s["crop_path"]).exists():
            crop_ok += 1
        if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists():
            overlay_ok += 1
    lines += [
        f"- Crops generated: {crop_ok}/{len(slots)}",
        f"- Overlays generated: {overlay_ok}/{len(slots)}",
        "",
        "### formula_slots.json → canonical_paper.md",
        "",
        f"- canonical_paper.md exists: {(accept_dir / 'canonical_paper.md').exists()}",
    ]
    canonical = (accept_dir / "canonical_paper.md").read_text(encoding="utf-8") if (accept_dir / "canonical_paper.md").exists() else ""
    matched = sum(1 for s in slots if s["formula_id"] in canonical)
    lines += [
        f"- Formulas referenced in canonical: {matched}/{len(slots)}",
        "",
        "### formula_slots.json → visual_audit/",
        "",
        f"- visual_audit/index.html exists: {(accept_dir / 'visual_audit' / 'index.html').exists()}",
        f"- Per-formula HTML: {sum(1 for s in slots if (accept_dir / 'visual_audit' / (s['formula_id'] + '.html')).exists())}/{len(slots)}",
        "",
        "## Conclusion",
        "",
    ]
    all_ok = (
        (accept_dir / "source.pdf").exists()
        and (accept_dir / "document_blocks.json").exists()
        and (accept_dir / "formula_slots.json").exists()
        and (accept_dir / "canonical_paper.md").exists()
        and crop_ok == len(slots)
        and overlay_ok == len(slots)
    )
    if all_ok:
        lines.append("All artifacts are present and traceable. Machine gate: PASS.")
    else:
        lines.append("Some artifacts are missing or incomplete. Machine gate: CHECK REQUIRED.")
    lines += [
        "",
        "Note: This is a machine-generated traceability report. "
        "Manual visual verification is required to confirm formula correctness.",
    ]
    (accept_dir / "compare_report.md").write_text("\n".join(lines), encoding="utf-8")


def generate_quality_report(accept_dir: Path, result, meta: dict) -> None:
    """Generate quality report."""
    slots = result.formula_slots
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]

    lines = [
        "# M1 Quality Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Paper Search Result",
        "",
        f"- Paper: {meta['title']} (arXiv {meta['arxiv_id']})",
        f"- Search query: `{meta['search_query_that_found_it']}`",
        f"- Formula pre-screen: {meta['formula_prescreen_count']}",
        "",
        "## Machine Gate Result",
        "",
        f"- Quality status: **{result.quality.status.value}**",
        f"- M2 ready: **{result.canonicalization.m2_ready}**",
        f"- Blocking reasons: {'; '.join(result.quality.blocking_reasons) or 'none'}",
        f"- Warning reasons: {'; '.join(result.quality.warning_reasons) or 'none'}",
        "",
        "## Manual Visual Verification",
        "",
        "**Status: PENDING**",
        "",
        "Codex cannot perform manual visual verification. "
        "The user must review the acceptance package and verify each formula.",
        "",
        "## Known Risks",
        "",
    ]
    for s in slots:
        if s.get("risk_flags"):
            lines.append(f"- {s['formula_id']}: {', '.join(s['risk_flags'])}")
    if not any(s.get("risk_flags") for s in slots):
        lines.append("- None")

    lines += [
        "",
        "## Exclusion Summary",
        "",
        f"- Reference formulas excluded: {len(ref_slots)}",
        f"- Dense raw-only excluded: {sum(1 for s in body_slots if not s.get('final_latex') and len(body_slots) >= 5)}",
        f"- Section contradiction: {result.quality.section_contradiction_count}",
        f"- All-formulas-in-Abstract: {result.quality.all_formulas_in_abstract_suspicious}",
    ]
    (accept_dir / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def create_zip(source_dir: Path, zip_path: Path) -> None:
    """Create zip from acceptance directory."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(source_dir.parent)
                zf.write(file, arcname)


if __name__ == "__main__":
    sys.exit(main())
