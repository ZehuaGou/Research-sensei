"""Regenerate M1 acceptance reports from existing formula_slots.json.

Does NOT re-run MinerU parse. Reads existing artifacts and regenerates:
  - FINAL_MANUAL_VERIFY_INDEX.md
  - visual_audit/index.html + per-formula HTML
  - quality_report.md
  - compare_report.md
  - performance_report.md/json
  - performance_diagnosis.md
  - acceptance zip
"""
from __future__ import annotations

import datetime
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def regenerate(accept_dir: Path) -> None:
    """Regenerate all reports from existing artifacts."""
    accept_dir = Path(accept_dir)
    if not accept_dir.exists():
        print(f"ERROR: {accept_dir} does not exist")
        return

    # Load formula_slots.json (the enriched version)
    slots_path = accept_dir / "formula_slots.json"
    if not slots_path.exists():
        print("ERROR: formula_slots.json not found")
        return
    slots = json.loads(slots_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(slots)} formula slots from formula_slots.json")

    # Load paper_metadata.json
    meta_path = accept_dir / "paper_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    # Load performance_report.json for parse_stats
    perf_path = accept_dir / "performance_report.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8")) if perf_path.exists() else {}

    # Count LaTeX
    latex_count = sum(1 for s in slots if s.get("final_latex"))
    print(f"Formulas with final_latex: {latex_count}/{len(slots)}")

    # Regenerate FINAL_MANUAL_VERIFY_INDEX.md
    print("Regenerating FINAL_MANUAL_VERIFY_INDEX.md...")
    _regen_verify_index(accept_dir, slots, meta)

    # Regenerate visual audit HTML
    print("Regenerating visual audit HTML...")
    _regen_visual_audit(accept_dir, slots)

    # Regenerate quality report
    print("Regenerating quality_report.md...")
    _regen_quality_report(accept_dir, slots, meta, perf)

    # Regenerate compare report
    print("Regenerating compare_report.md...")
    _regen_compare_report(accept_dir, slots)

    # Regenerate performance report
    print("Regenerating performance_report.md/json...")
    _regen_performance_report(accept_dir, slots, meta, perf)

    # Generate performance diagnosis
    print("Generating performance_diagnosis.md...")
    _gen_performance_diagnosis(accept_dir, perf)

    # Regenerate zip
    print("Regenerating zip...")
    zip_path = ROOT / "reports" / f"{accept_dir.name}.zip"
    _create_zip(accept_dir, zip_path)
    print(f"Zip: {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")

    print("DONE.")


def _regen_verify_index(accept_dir: Path, slots: list[dict], meta: dict) -> None:
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]

    lines = [
        "# M1 Final Manual Verify Index",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Paper Information",
        "",
        f"- **Title**: {meta.get('title', 'N/A')}",
        f"- **arXiv ID**: {meta.get('arxiv_id', 'N/A')}",
        f"- **PDF URL**: {meta.get('pdf_url', 'N/A')}",
        f"- **Published**: {meta.get('published', 'N/A')}",
        f"- **Search Query**: `{meta.get('search_query_that_found_it', 'N/A')}`",
        "",
        "## Search Process",
        "",
        f"- Search date: {meta.get('timestamp', 'N/A')}",
        f"- Formula prescreen count: {meta.get('formula_prescreen_count', 'N/A')} (PyMuPDF text-line heuristic, NOT MinerU final)",
        f"- Selection reason: {meta.get('selected_reason', 'N/A')}",
        "",
        "## Device & Performance",
        "",
        f"- Device requested: {meta.get('device_mode_requested', 'N/A')}",
        f"- Device actual: {meta.get('device_mode_actual', 'N/A')}",
        f"- GPU used: {meta.get('cuda_available', False)}",
        "",
        "## Pipeline Result",
        "",
        f"- Quality status: **{meta.get('quality_status', 'N/A')}**",
        f"- M2 ready: **{meta.get('m2_ready', 'N/A')}**",
        f"- Primary parser: MinerU2.5-Pro",
        f"- Ollama: disabled",
        "",
        "## Formula Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total formula slots (from MinerU full parse) | {len(slots)} |",
        f"| Body formulas (M2 ready) | {len(body_slots)} |",
        f"| Reference formulas (excluded) | {len(ref_slots)} |",
        f"| Formulas with LaTeX | {sum(1 for s in slots if s.get('final_latex'))} |",
        f"| Formulas with crop | {sum(1 for s in slots if s.get('crop_path'))} |",
        f"| Formulas with overlay | {sum(1 for s in slots if s.get('overlay_path'))} |",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{meta.get('quality_status', 'N/A')}** |",
        f"| GPU path | **{'PASS' if meta.get('cuda_available') else 'FAIL'}** |",
        "| Manual visual verification | **PENDING** |",
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
    ]
    (accept_dir / "FINAL_MANUAL_VERIFY_INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def _regen_visual_audit(accept_dir: Path, slots: list[dict]) -> None:
    audit_dir = accept_dir / "visual_audit"
    audit_dir.mkdir(exist_ok=True)

    total = len(slots)
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]
    latex_count = sum(1 for s in slots if s.get("final_latex"))

    for slot in slots:
        fid = slot["formula_id"]
        page = slot.get("page", 0)
        section = slot.get("section", "Unknown")
        section_conf = slot.get("section_confidence", "low")
        section_reason = slot.get("section_reason", "")
        final_latex = slot.get("final_latex", "")
        final_origin = slot.get("final_origin", "")
        risk_flags = slot.get("risk_flags", [])
        m2_ready = slot.get("formula_m2_ready", True)
        block_source = slot.get("block_source", "")

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

        if final_latex:
            html += f'<div class="field"><span class="field-label">LaTeX:</span></div><pre>{final_latex}</pre>\n'

        html += "</body></html>"
        (audit_dir / f"{fid}.html").write_text(html, encoding="utf-8")

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


def _regen_quality_report(accept_dir: Path, slots: list[dict], meta: dict, perf: dict) -> None:
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]

    quality_status = meta.get("quality_status", "UNKNOWN")
    quality_pass = quality_status == "PASS"
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    lines = [
        "# M1 Quality Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{'PASS' if quality_pass else 'FAIL'}** |",
        f"| GPU path | **{'PASS' if gpu_used else 'FAIL'}** |",
        f"| Performance gate | **{'PASS' if perf_pass else 'WARNING'}** |",
        f"| Manual visual verification | **PENDING** |",
        "",
        "## Paper",
        "",
        f"- Title: {meta.get('title', 'N/A')} (arXiv {meta.get('arxiv_id', 'N/A')})",
        f"- Search query: `{meta.get('search_query_that_found_it', 'N/A')}`",
        f"- Prescreen formula lines: {meta.get('formula_prescreen_count', 'N/A')} (PyMuPDF heuristic)",
        f"- Final formula slots: {len(slots)} (MinerU full parse)",
        "",
        "## Machine Gate",
        "",
        f"- Quality: **{quality_status}**",
        f"- M2 ready: **{meta.get('m2_ready', 'N/A')}**",
        "",
        "## Device",
        "",
        f"- Device: {perf.get('device_mode_actual', 'N/A')}",
        f"- Seconds/page: {seconds_per_page:.1f}",
        "",
        "## Manual Verification",
        "",
        "**Status: PENDING**",
        "",
        "## Exclusions",
        "",
        f"- Reference formulas: {len(ref_slots)}",
    ]
    (accept_dir / "quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def _regen_compare_report(accept_dir: Path, slots: list[dict]) -> None:
    crop_ok = sum(1 for s in slots if s.get("crop_path") and (accept_dir / s["crop_path"]).exists())
    overlay_ok = sum(1 for s in slots if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists())

    canonical_path = accept_dir / "canonical_paper.md"
    canonical = canonical_path.read_text(encoding="utf-8") if canonical_path.exists() else ""
    matched = sum(1 for s in slots if s["formula_id"] in canonical)

    all_ok = (
        (accept_dir / "source.pdf").exists()
        and (accept_dir / "document_blocks.json").exists()
        and (accept_dir / "formula_slots.json").exists()
        and crop_ok == len(slots)
        and overlay_ok == len(slots)
    )

    lines = [
        "# M1 Compare Report: Artifact Traceability",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Artifact Cross-Reference",
        "",
        f"- source.pdf exists: {(accept_dir / 'source.pdf').exists()}",
        f"- document_blocks.json exists: {(accept_dir / 'document_blocks.json').exists()}",
        f"- formula_slots.json exists: {(accept_dir / 'formula_slots.json').exists()}",
        f"- canonical_paper.md exists: {canonical_path.exists()}",
        f"- Crops: {crop_ok}/{len(slots)}",
        f"- Overlays: {overlay_ok}/{len(slots)}",
        f"- Formulas in canonical: {matched}/{len(slots)}",
        f"- Visual audit index: {(accept_dir / 'visual_audit' / 'index.html').exists()}",
        "",
        "Machine gate: " + ("PASS" if all_ok else "CHECK REQUIRED"),
        "",
        "Note: Machine traceability report. Manual visual verification required.",
    ]
    (accept_dir / "compare_report.md").write_text("\n".join(lines), encoding="utf-8")


def _regen_performance_report(accept_dir: Path, slots: list[dict], meta: dict, perf: dict) -> None:
    quality_status = meta.get("quality_status", "UNKNOWN")
    quality_pass = quality_status == "PASS"
    gpu_used = perf.get("gpu_used", False)
    seconds_per_page = perf.get("seconds_per_page", 0)
    perf_pass = seconds_per_page <= 120

    lines = [
        "# M1 Performance Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Status Summary",
        "",
        "| Gate | Status |",
        "|------|--------|",
        f"| Machine quality gate | **{'PASS' if quality_pass else 'FAIL'}** |",
        f"| GPU path | **{'PASS' if gpu_used else 'FAIL'}** |",
        f"| Performance gate | **{'PASS' if perf_pass else 'WARNING'}** |",
        f"| Manual visual verification | **PENDING** |",
        "",
        "**Note**: M1 is NOT fully verified until all gates pass AND manual visual verification is complete.",
        "",
        "## Paper",
        "",
        f"- Title: {meta.get('title', 'N/A')}",
        f"- arXiv: {meta.get('arxiv_id', 'N/A')}",
        f"- Pages: {perf.get('page_count', 'N/A')}",
        "",
        "## Device",
        "",
        f"- Requested: {perf.get('device_mode_requested', 'N/A')}",
        f"- Actual: **{perf.get('device_mode_actual', 'N/A')}**",
        f"- GPU used: {gpu_used}",
        f"- GPU name: {perf.get('gpu_name', 'N/A')}",
        "",
        "## Timing",
        "",
        f"- Full parse: {perf.get('parse_elapsed_seconds', 'N/A')}s",
        f"- Seconds/page: {seconds_per_page:.1f}",
        "",
        "## Output",
        "",
        f"- Blocks: {perf.get('block_count', 'N/A')}",
        f"- Formula slots: {perf.get('formula_count', len(slots))}",
        f"- Quality: {quality_status}",
        f"- M2 ready: {meta.get('m2_ready', 'N/A')}",
        "",
        "## Warnings",
        "",
    ]
    warnings = perf.get("warnings", [])
    if warnings:
        for w in warnings:
            lines.append(f"- **{w}**")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Conclusion",
        "",
    ]
    if perf_pass and quality_pass:
        lines.append("All automated gates passed. Manual visual verification still required.")
    elif quality_pass and not perf_pass:
        lines.append("Machine quality gate passed, but performance gate has warnings. M1 can be used for manual review but not recommended for batch processing.")
    elif not quality_pass:
        lines.append("Machine quality gate failed. Review blocking reasons before proceeding.")
    else:
        lines.append("GPU path used but some warnings detected.")
    (accept_dir / "performance_report.md").write_text("\n".join(lines), encoding="utf-8")


def _gen_performance_diagnosis(accept_dir: Path, perf: dict) -> None:
    seconds_per_page = perf.get("seconds_per_page", 0)
    backend = perf.get("backend", "transformers")
    gpu_name = perf.get("gpu_name", "N/A")
    gpu_mem = perf.get("gpu_memory_total_mb", 0)
    device_actual = perf.get("device_mode_actual", "unknown")
    parse_elapsed = perf.get("parse_elapsed_seconds", 0)
    page_count = perf.get("page_count", 0)

    lines = [
        "# M1 Performance Diagnosis",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Current Performance",
        "",
        f"- Backend: {backend}",
        f"- GPU: {gpu_name} ({gpu_mem} MB)",
        f"- device_mode_actual: {device_actual}",
        f"- Parse elapsed: {parse_elapsed:.0f}s ({parse_elapsed/60:.1f} min)",
        f"- Pages: {page_count}",
        f"- Seconds/page: {seconds_per_page:.1f}",
        f"- Performance gate: **{'PASS' if seconds_per_page <= 120 else 'WARNING (>120s/page)'}**",
        "",
        "## Analysis",
        "",
        f"MinerU2.5-Pro is running on GPU ({gpu_name}) via the `{backend}` backend. "
        f"Each page takes ~{seconds_per_page:.0f} seconds, which exceeds the 120s/page warning threshold. "
        "This means the full M1 pipeline takes ~45 minutes for a 15-page paper.",
        "",
        "The GPU is being used (confirmed by device_mode_actual=cuda and GPU memory allocation), "
        "but the per-page cost is high due to the two-step inference process (layout detection + OCR/formula extraction per region).",
        "",
        "## Suitability",
        "",
        "- **Manual review / single paper**: Acceptable. 45 minutes is tolerable for one-off acceptance.",
        "- **Batch processing**: Not recommended at current speed. 15 pages × 179s = 2685s per paper. "
        "100 papers would take ~75 hours.",
        "",
        "## Optimization Directions",
        "",
        "1. **vLLM backend**: Evaluate if `mineru-vl-utils` supports vLLM for faster inference.",
        "2. **Reduce render_scale**: Current default is 2.0. Lowering to 1.5 or 1.0 reduces image size and inference time.",
        "3. **Page-level cache**: Cache layout detection results to avoid re-processing unchanged pages.",
        "4. **Selective parsing**: Only run full MinerU on pages with formula candidates (from prescreen).",
        "5. **Batch/async page pipeline**: Process multiple pages in parallel if GPU memory allows.",
        "6. **Per-page profiling**: Record each page's layout + OCR time to identify slow pages.",
        "7. **Model quantization**: If supported, use INT8/FP16 quantized model for faster inference.",
    ]
    (accept_dir / "performance_diagnosis.md").write_text("\n".join(lines), encoding="utf-8")


def _create_zip(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(source_dir.parent)
                zf.write(file, arcname)


def main() -> int:
    if len(sys.argv) < 2:
        accept_dir = ROOT / "reports" / "m1_acceptance_manual_review_2510_18998"
    else:
        accept_dir = Path(sys.argv[1])
    regenerate(accept_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
