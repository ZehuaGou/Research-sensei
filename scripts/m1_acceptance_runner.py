"""M1 Acceptance Runner — run full M1 pipeline on a searched paper and generate acceptance package.

Reads selected_paper_metadata.json from reports/m1_unseen_paper_search/, runs
MinerU2.5-Pro → RuleBasedStructureRefiner → CanonicalBuilder → M1QualityGate,
generates visual audit, performance report, and packages everything into a zip.
"""
from __future__ import annotations

import argparse
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="M1 Acceptance Runner")
    p.add_argument("--device-mode", choices=["auto", "cuda", "cpu"], default="auto")
    p.add_argument("--search-dir", type=str, default=None)
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument("--enable-ollama-latex", action="store_true", help="Run Ollama formula LaTeX polishing after MinerU extraction.")
    p.add_argument("--ollama-latex-model", default="qwen3.5:4b", help="Vision-capable Ollama model for formula LaTeX polishing.")
    p.add_argument("--ollama-base-url", default="http://localhost:11434")
    p.add_argument("--ollama-timeout", type=float, default=30.0)
    p.add_argument("--ollama-min-confidence", type=float, default=0.8)
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    search_dir = Path(args.search_dir) if args.search_dir else SEARCH_DIR

    print("=" * 60)
    print("M1 Acceptance Runner")
    print("=" * 60)

    # Load selected paper metadata
    meta_path = search_dir / "selected_paper_metadata.json"
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
    print(f"Device mode: {args.device_mode}")
    print(f"Ollama LaTeX polish: {args.enable_ollama_latex}")

    # Create acceptance directory
    accept_dir = Path(args.output_dir) if args.output_dir else ROOT / "reports" / f"m1_acceptance_manual_review_{paper_id}"
    accept_dir.mkdir(parents=True, exist_ok=True)

    # Copy source PDF
    t_copy_start = time.perf_counter()
    source_pdf = accept_dir / "source.pdf"
    shutil.copy2(pdf_path, source_pdf)
    t_copy = time.perf_counter() - t_copy_start
    print(f"Copied source.pdf ({source_pdf.stat().st_size} bytes)")

    # Get PDF page count
    with fitz.open(str(source_pdf)) as doc:
        page_count = len(doc)

    # Run M1 pipeline
    print("\n[1/7] Running MinerU2.5-Pro pipeline...")
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter
    from researchsensei.canonical.ollama_latex_validator import OllamaLatexValidator
    from researchsensei.canonical.ollama_refiner import OllamaStructuredClient
    from researchsensei.canonical.pipeline import M1CanonicalPipeline

    adapter = MinerU25ProAdapter(device_mode=args.device_mode)
    latex_validator = None
    if args.enable_ollama_latex:
        latex_validator = OllamaLatexValidator(
            client=OllamaStructuredClient(
                base_url=args.ollama_base_url,
                model=args.ollama_latex_model,
                timeout_seconds=args.ollama_timeout,
                max_retries=0,
            ),
            model=args.ollama_latex_model,
            min_confidence=args.ollama_min_confidence,
        )
    pipeline = M1CanonicalPipeline(mineru_adapter=adapter, latex_validator=latex_validator)

    t_pipeline_start = time.perf_counter()
    result = pipeline.run_pdf(
        paper_id=paper_id,
        title=title,
        pdf_path=source_pdf,
        output_dir=accept_dir,
        apply_ollama=False,
        apply_ollama_latex=args.enable_ollama_latex,
    )
    t_pipeline = time.perf_counter() - t_pipeline_start

    # Extract device stats from pipeline result
    device_stats = result.metrics if hasattr(result, 'metrics') else {}
    parse_stats = {}
    raw_path = accept_dir / "raw_mineru_output.json"
    if raw_path.exists():
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        parse_stats = raw.get("stats", {})

    print(f"  Pipeline completed in {t_pipeline:.1f}s")
    print(f"  Quality: {result.quality.status.value}")
    print(f"  M2 ready: {result.canonicalization.m2_ready}")
    print(f"  Formula slots: {len(result.formula_slots)}")
    print(f"  Blocks: {len(result.blocks)}")
    print(f"  Device: {parse_stats.get('device_mode_actual', 'unknown')}")

    # Enrich result.formula_slots with data from formula_slots.json
    # (CanonicalBuilder writes enriched slots with final_latex, mineru_latex, section, etc.
    #  but result.formula_slots only has raw slots from the pipeline)
    enriched_slots_path = accept_dir / "formula_slots.json"
    if enriched_slots_path.exists():
        enriched = json.loads(enriched_slots_path.read_text(encoding="utf-8"))
        if len(enriched) == len(result.formula_slots):
            result.formula_slots = enriched
            print(f"  Enriched formula_slots from formula_slots.json (final_latex: {sum(1 for s in enriched if s.get('final_latex'))})")

    # Copy search artifacts
    print("\n[2/7] Copying search artifacts...")
    for name in [
        "search_config.json", "metadata_candidates.json", "candidate_papers.json",
        "rejected_candidates.md", "selected_paper_metadata.json", "paper_search_report.md",
    ]:
        src = search_dir / name
        if src.exists():
            shutil.copy2(src, accept_dir / name)

    # Generate visual audit
    print("\n[3/7] Generating visual audit...")
    t_audit_start = time.perf_counter()
    generate_visual_audit(accept_dir, result)
    t_audit = time.perf_counter() - t_audit_start

    # Generate verify index
    print("\n[4/7] Generating verification index...")
    generate_verify_index(accept_dir, result, meta, parse_stats)

    # Generate compare and quality reports
    generate_compare_report(accept_dir, result)
    generate_quality_report(accept_dir, result, meta, parse_stats)

    # Generate performance report
    print("\n[5/7] Generating performance report...")
    t_zip_start = time.perf_counter()
    generate_performance_report(
        accept_dir, result, meta, parse_stats,
        page_count=page_count,
        pdf_size_bytes=source_pdf.stat().st_size,
        pipeline_elapsed=t_pipeline,
        audit_elapsed=t_audit,
        device_mode=args.device_mode,
    )

    # Write paper_metadata.json
    print("\n[6/7] Writing paper metadata...")
    paper_meta = {
        **meta,
        "pipeline_elapsed_seconds": round(t_pipeline, 3),
        "quality_status": result.quality.status.value,
        "m2_ready": result.canonicalization.m2_ready,
        "formula_slot_count": len(result.formula_slots),
        "block_count": len(result.blocks),
        "primary_parser": "mineru25pro",
        "ollama_enabled": False,
        "device_mode_requested": parse_stats.get("device_mode_requested", args.device_mode),
        "device_mode_actual": parse_stats.get("device_mode_actual", "unknown"),
        "cuda_available": parse_stats.get("cuda_available", False),
        "gpu_name": parse_stats.get("gpu_name"),
        "seconds_per_page": parse_stats.get("seconds_per_page"),
        "perf_warnings": parse_stats.get("perf_warnings", []),
    }
    (accept_dir / "paper_metadata.json").write_text(
        json.dumps(paper_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Create zip
    print("\n[7/7] Creating zip package...")
    zip_path = ROOT / "reports" / f"m1_acceptance_manual_review_{paper_id}.zip"
    create_zip(accept_dir, zip_path)
    t_zip = time.perf_counter() - t_zip_start
    print(f"  Zip: {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")

    # Summary
    total_time = t_copy + t_pipeline + t_audit + t_zip
    print(f"\n{'=' * 60}")
    print(f"PERFORMANCE SUMMARY")
    print(f"  Pages: {page_count}")
    print(f"  PDF size: {source_pdf.stat().st_size / 1024:.0f} KB")
    print(f"  Device: {parse_stats.get('device_mode_actual', 'unknown')}")
    print(f"  Parse time: {t_pipeline:.1f}s ({parse_stats.get('seconds_per_page', 0):.1f}s/page)")
    print(f"  Formulas: {len(result.formula_slots)}")
    print(f"  Blocks: {len(result.blocks)}")
    print(f"  Total runtime: {total_time:.1f}s")
    print(f"{'=' * 60}")
    print(f"\nDONE. Acceptance package: {accept_dir}")
    return 0


def generate_performance_report(
    accept_dir: Path, result, meta: dict, parse_stats: dict,
    *, page_count: int, pdf_size_bytes: int,
    pipeline_elapsed: float, audit_elapsed: float,
    device_mode: str,
) -> None:
    """Generate performance_report.md and performance_report.json."""
    device_actual = parse_stats.get("device_mode_actual", "unknown")
    gpu_used = device_actual == "cuda"
    fallback_reason = parse_stats.get("fallback_reason")
    seconds_per_page = parse_stats.get("seconds_per_page", 0)
    perf_warnings = parse_stats.get("perf_warnings", [])

    # Performance thresholds
    warnings = list(perf_warnings)
    if device_actual == "cpu" and device_mode != "cpu":
        warnings.append("GPU requested/available but running on CPU")
    if seconds_per_page > 120:
        warnings.append(f"seconds_per_page={seconds_per_page:.0f} > 120s threshold")
    if pipeline_elapsed > 3600:
        warnings.append(f"total_parse_time={pipeline_elapsed:.0f}s > 3600s threshold")

    report_json = {
        "timestamp": datetime.datetime.now().isoformat(),
        "paper_id": meta.get("paper_id", ""),
        "arxiv_id": meta.get("arxiv_id", ""),
        "page_count": page_count,
        "pdf_size_bytes": pdf_size_bytes,
        "pdf_size_mb": round(pdf_size_bytes / 1024 / 1024, 2),
        "device_mode_requested": device_mode,
        "device_mode_actual": device_actual,
        "gpu_used": gpu_used,
        "cuda_available": parse_stats.get("cuda_available", False),
        "gpu_name": parse_stats.get("gpu_name"),
        "gpu_memory_total_mb": parse_stats.get("gpu_memory_total_mb"),
        "fallback_reason": fallback_reason,
        "backend": parse_stats.get("model_load_backend", "transformers"),
        "model_load_seconds": parse_stats.get("model_load_seconds", 0),
        "parse_elapsed_seconds": parse_stats.get("elapsed_seconds", round(pipeline_elapsed, 1)),
        "seconds_per_page": seconds_per_page,
        "pages_per_second": parse_stats.get("pages_per_second", 0),
        "block_count": len(result.blocks),
        "formula_count": len(result.formula_slots),
        "quality_status": result.quality.status.value,
        "audit_elapsed_seconds": round(audit_elapsed, 1),
        "pipeline_total_seconds": round(pipeline_elapsed, 1),
        "warnings": warnings,
        "perf_pass": len(warnings) == 0,
    }
    (accept_dir / "performance_report.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    perf_pass = len(warnings) == 0
    quality_pass = result.quality.status.value == "PASS"

    md_lines = [
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
        f"- Title: {meta.get('title', '')}",
        f"- arXiv: {meta.get('arxiv_id', '')}",
        f"- Pages: {page_count}",
        f"- PDF size: {pdf_size_bytes / 1024:.0f} KB",
        "",
        "## Device",
        "",
        f"- Requested: {device_mode}",
        f"- Actual: **{device_actual}**",
        f"- GPU used: {gpu_used}",
        f"- CUDA available: {parse_stats.get('cuda_available', False)}",
        f"- GPU name: {parse_stats.get('gpu_name', 'N/A')}",
        f"- GPU memory: {parse_stats.get('gpu_memory_total_mb', 'N/A')} MB",
        f"- Fallback reason: {fallback_reason or 'none'}",
        "",
        "## Timing",
        "",
        f"- Model load: {parse_stats.get('model_load_seconds', 0):.1f}s",
        f"- Full parse: {parse_stats.get('elapsed_seconds', round(pipeline_elapsed, 1)):.1f}s",
        f"- Seconds/page: {seconds_per_page:.1f}",
        f"- Pages/second: {parse_stats.get('pages_per_second', 0):.2f}",
        f"- Visual audit: {audit_elapsed:.1f}s",
        f"- Total pipeline: {pipeline_elapsed:.1f}s",
        "",
        "## Output",
        "",
        f"- Blocks: {len(result.blocks)}",
        f"- Formula slots: {len(result.formula_slots)}",
        f"- Quality: {result.quality.status.value}",
        f"- M2 ready: {result.canonicalization.m2_ready}",
        "",
        "## Warnings",
        "",
    ]
    if warnings:
        for w in warnings:
            md_lines.append(f"- **{w}**")
    else:
        md_lines.append("- None")
    md_lines += [
        "",
        "## Conclusion",
        "",
    ]
    if perf_pass and quality_pass:
        md_lines.append("All automated gates passed. Manual visual verification still required.")
    elif quality_pass and not perf_pass:
        md_lines.append("Machine quality gate passed, but performance gate has warnings. M1 can be used for manual review but not recommended for batch processing.")
    elif not quality_pass:
        md_lines.append("Machine quality gate failed. Review blocking reasons before proceeding.")
    else:
        md_lines.append("GPU path used but some warnings detected.")
    (accept_dir / "performance_report.md").write_text("\n".join(md_lines), encoding="utf-8")


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


def generate_verify_index(accept_dir: Path, result, meta: dict, parse_stats: dict) -> None:
    """Generate FINAL_MANUAL_VERIFY_INDEX.md."""
    slots = result.formula_slots
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]

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
        f"- Formula prescreen count: {meta['formula_prescreen_count']} (PyMuPDF text-line heuristic, NOT MinerU final)",
        f"- Selection reason: {meta['selected_reason']}",
        "",
        "## Device & Performance",
        "",
        f"- Device requested: {parse_stats.get('device_mode_requested', 'auto')}",
        f"- Device actual: {parse_stats.get('device_mode_actual', 'unknown')}",
        f"- GPU used: {parse_stats.get('device_mode_actual') == 'cuda'}",
        f"- Seconds per page: {parse_stats.get('seconds_per_page', 0):.1f}",
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
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total formula slots (from MinerU full parse) | {len(slots)} |",
        f"| Body formulas (M2 ready) | {len(body_slots)} |",
        f"| Reference formulas (excluded) | {len(ref_slots)} |",
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
        f"- source.pdf exists: {(accept_dir / 'source.pdf').exists()}",
        f"- document_blocks.json exists: {(accept_dir / 'document_blocks.json').exists()}",
        f"- formula_slots.json exists: {(accept_dir / 'formula_slots.json').exists()}",
        f"- canonical_paper.md exists: {(accept_dir / 'canonical_paper.md').exists()}",
        f"- Blocks: {len(result.blocks)}",
        f"- Formula slots: {len(slots)}",
        "",
    ]
    crop_ok = sum(1 for s in slots if s.get("crop_path") and (accept_dir / s["crop_path"]).exists())
    overlay_ok = sum(1 for s in slots if s.get("overlay_path") and (accept_dir / s["overlay_path"]).exists())
    lines += [
        f"- Crops: {crop_ok}/{len(slots)}",
        f"- Overlays: {overlay_ok}/{len(slots)}",
    ]
    canonical = (accept_dir / "canonical_paper.md").read_text(encoding="utf-8") if (accept_dir / "canonical_paper.md").exists() else ""
    matched = sum(1 for s in slots if s["formula_id"] in canonical)
    lines += [
        f"- Formulas in canonical: {matched}/{len(slots)}",
        f"- Visual audit index: {(accept_dir / 'visual_audit' / 'index.html').exists()}",
    ]
    all_ok = (
        (accept_dir / "source.pdf").exists()
        and (accept_dir / "document_blocks.json").exists()
        and (accept_dir / "formula_slots.json").exists()
        and crop_ok == len(slots)
        and overlay_ok == len(slots)
    )
    lines += [
        "",
        "Machine gate: " + ("PASS" if all_ok else "CHECK REQUIRED"),
        "",
        "Note: Machine traceability report. Manual visual verification required.",
    ]
    (accept_dir / "compare_report.md").write_text("\n".join(lines), encoding="utf-8")


def generate_quality_report(accept_dir: Path, result, meta: dict, parse_stats: dict) -> None:
    """Generate quality report."""
    slots = result.formula_slots
    body_slots = [s for s in slots if s.get("formula_m2_ready", True)]
    ref_slots = [s for s in slots if not s.get("formula_m2_ready", True)]

    quality_pass = result.quality.status.value == "PASS"
    gpu_used = parse_stats.get("device_mode_actual") == "cuda"
    seconds_per_page = parse_stats.get("seconds_per_page", 0)
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
        f"- Title: {meta['title']} (arXiv {meta['arxiv_id']})",
        f"- Search query: `{meta['search_query_that_found_it']}`",
        f"- Prescreen formula lines: {meta['formula_prescreen_count']} (PyMuPDF heuristic)",
        f"- Final formula slots: {len(slots)} (MinerU full parse)",
        "",
        "## Machine Gate",
        "",
        f"- Quality: **{result.quality.status.value}**",
        f"- M2 ready: **{result.canonicalization.m2_ready}**",
        f"- Blocking: {'; '.join(result.quality.blocking_reasons) or 'none'}",
        f"- Warnings: {'; '.join(result.quality.warning_reasons) or 'none'}",
        "",
        "## Device",
        "",
        f"- Device: {parse_stats.get('device_mode_actual', 'unknown')}",
        f"- Seconds/page: {seconds_per_page:.1f}",
        f"- Warnings: {'; '.join(parse_stats.get('perf_warnings', [])) or 'none'}",
        "",
        "## Manual Verification",
        "",
        "**Status: PENDING**",
        "",
        "## Exclusions",
        "",
        f"- Reference formulas: {len(ref_slots)}",
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
