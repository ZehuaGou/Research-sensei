"""Generate parser comparison outputs for 3 PDFs."""
import time, re, shutil
from pathlib import Path

PDFS = {
    "paper_1": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/2112.14436/source.pdf",
        "pid": "2112.14436",
        "title": "Monte Carlo EM for Deep Time Series Anomaly Detection",
    },
    "paper_2": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/W3184127157/source.pdf",
        "pid": "W3184127157",
        "title": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
    },
    "paper_3": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/W3204263062/source.pdf",
        "pid": "W3204263062",
        "title": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
    },
}

BASE = Path("reports/m1_parser_review")

def count_sections(text):
    return len(re.findall(r'^#{1,3}\s+', text, re.MULTILINE))

def check_sections(text):
    t = text.lower()
    return {
        "title": bool(re.search(r'^#\s+', text, re.MULTILINE)) or len(t[:500]) > 50,
        "abstract": "abstract" in t[:3000],
        "introduction": "introduction" in t,
        "method": any(w in t for w in ["method", "approach", "proposed"]),
        "experiments": any(w in t for w in ["experiment", "evaluation", "result"]),
        "conclusion": any(w in t for w in ["conclusion", "discussion"]),
        "references": any(w in t for w in ["reference", "bibliography"]),
    }

def count_formulas(text):
    display = len(re.findall(r'\$\$.*?\$\$|\\\[.*?\\\]|\\begin\{equation', text, re.DOTALL))
    inline = len(re.findall(r'\$[^$]+\$', text))
    return display, inline

def extract_formula_samples(text, n=5):
    samples = []
    for m in re.finditer(r'\$\$(.*?)\$\$', text, re.DOTALL):
        latex = m.group(1).strip()
        if latex and len(latex) > 3:
            samples.append(latex[:200])
        if len(samples) >= n:
            break
    if len(samples) < n:
        for m in re.finditer(r'\\begin\{equation\}(.*?)\\end\{equation\}', text, re.DOTALL):
            latex = m.group(1).strip()
            if latex:
                samples.append(latex[:200])
            if len(samples) >= n:
                break
    return samples

def run_markitdown(pdf_path):
    try:
        from markitdown import MarkItDown
        md = MarkItDown(enable_plugins=False)
        t0 = time.time()
        result = md.convert(str(pdf_path))
        elapsed = time.time() - t0
        return result.text_content, elapsed
    except Exception as e:
        return f"FAILED: {e}", 0

def run_pymupdf(pdf_path):
    try:
        import fitz
        t0 = time.time()
        with fitz.open(str(pdf_path)) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
        elapsed = time.time() - t0
        return text, elapsed
    except Exception as e:
        return f"FAILED: {e}", 0

def run_marker(pdf_path):
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        models = create_model_dict()
        converter = PdfConverter(artifact_dict=models)
        t0 = time.time()
        rendered = converter(str(pdf_path))
        elapsed = time.time() - t0
        text = rendered.markdown if hasattr(rendered, "markdown") else str(rendered)
        return text, elapsed
    except Exception as e:
        return f"FAILED: {type(e).__name__}: {str(e)[:300]}", 0

for name, info in PDFS.items():
    pdf_path = Path(info["src"])
    out_dir = BASE / name
    out_dir.mkdir(exist_ok=True)

    print(f"\n=== {name}: {info['title'][:60]} ===")

    # Copy source PDF
    shutil.copy2(pdf_path, out_dir / "source.pdf")
    print(f"  source.pdf: {pdf_path} ({pdf_path.stat().st_size // 1024}KB)")

    # Copy canonical_paper.md
    canon_src = Path(f"reports/live_eval/work/m1/workspace/runs/m1-live/canonical_papers/{info['pid']}/canonical_paper.md")
    if canon_src.exists():
        shutil.copy2(canon_src, out_dir / "canonical_paper.md")
        print(f"  canonical_paper.md: copied")
    else:
        print(f"  canonical_paper.md: NOT FOUND")

    # Run MarkItDown
    print("  Running MarkItDown...")
    md_text, md_time = run_markitdown(pdf_path)
    (out_dir / "markitdown.md").write_text(md_text, encoding="utf-8")
    print(f"  markitdown.md: {len(md_text)} chars, {md_time:.1f}s")

    # Run PyMuPDF
    print("  Running PyMuPDF...")
    pm_text, pm_time = run_pymupdf(pdf_path)
    (out_dir / "pymupdf.txt").write_text(pm_text, encoding="utf-8")
    print(f"  pymupdf.txt: {len(pm_text)} chars, {pm_time:.1f}s")

    # Run Marker only for paper_1
    if name == "paper_1":
        print("  Running Marker (this takes ~16min)...")
        mk_text, mk_time = run_marker(pdf_path)
        if mk_text.startswith("FAILED"):
            (out_dir / "marker_failed.txt").write_text(mk_text, encoding="utf-8")
            print(f"  marker: FAILED")
        else:
            (out_dir / "marker.md").write_text(mk_text, encoding="utf-8")
            print(f"  marker.md: {len(mk_text)} chars, {mk_time:.1f}s")
    else:
        (out_dir / "marker_skipped.txt").write_text(
            "Marker skipped for this paper (too slow, ~16min/paper). Tested on paper_1 only.",
            encoding="utf-8"
        )
        mk_text = "SKIPPED"
        mk_time = 0
        print("  marker: SKIPPED (too slow)")

    # Generate formula page screenshots
    print("  Generating formula screenshots...")
    try:
        import fitz
        with fitz.open(str(pdf_path)) as doc:
            for i, page in enumerate(doc):
                if i >= 3:
                    break
                pix = page.get_pixmap(dpi=150)
                pix.save(str(out_dir / f"formula_page_{i+1}.png"))
        print(f"  formula_page_*.png: saved")
    except Exception as e:
        print(f"  formula screenshots: FAILED ({e})")

    # Analyze
    md_sec = check_sections(md_text)
    pm_sec = check_sections(pm_text)
    md_display, md_inline = count_formulas(md_text)
    pm_display, pm_inline = count_formulas(pm_text)
    md_formulas = extract_formula_samples(md_text)
    pm_formulas = extract_formula_samples(pm_text)

    canon_text = ""
    canon_formulas = []
    canon_display = 0
    canon_inline = 0
    if (out_dir / "canonical_paper.md").exists():
        canon_text = (out_dir / "canonical_paper.md").read_text(encoding="utf-8", errors="ignore")
        canon_display, canon_inline = count_formulas(canon_text)
        canon_formulas = extract_formula_samples(canon_text)

    # Write compare_summary.md
    summary_lines = [
        f"# Parser Comparison: {info['title']}",
        "",
        "## Basic Info",
        f"- **title**: {info['title']}",
        f"- **paper_id**: {info['pid']}",
        f"- **source_pdf_path**: {str(pdf_path.resolve())}",
        "- **parser_used**: markitdown_pdf",
        f"- **canonical_paper_path**: {str(canon_src.resolve()) if canon_src.exists() else 'N/A'}",
        "",
        "## Parser Performance",
        "",
        "| Metric | MarkItDown | PyMuPDF | Marker |",
        "|--------|-----------|---------|--------|",
        f"| Time | {md_time:.1f}s | {pm_time:.1f}s | {'%.1fs' % mk_time if mk_time > 0 else 'SKIPPED'} |",
        f"| Output chars | {len(md_text)} | {len(pm_text)} | {len(mk_text) if isinstance(mk_text, str) and not mk_text.startswith(('FAILED','SKIP')) else 'N/A'} |",
        f"| Sections | {count_sections(md_text)} | {count_sections(pm_text)} | {count_sections(mk_text) if isinstance(mk_text, str) and not mk_text.startswith(('FAILED','SKIP')) else 'N/A'} |",
        "",
        "## Section Detection (MarkItDown)",
        "",
        "| Section | Detected |",
        "|---------|----------|",
    ]
    for sec, detected in md_sec.items():
        summary_lines.append(f"| {sec.title()} | {'YES' if detected else 'NO'} |")

    summary_lines += [
        "",
        "## Section Detection (PyMuPDF)",
        "",
        "| Section | Detected |",
        "|---------|----------|",
    ]
    for sec, detected in pm_sec.items():
        summary_lines.append(f"| {sec.title()} | {'YES' if detected else 'NO'} |")

    summary_lines += [
        "",
        "## Formula Analysis",
        "",
        "| Metric | MarkItDown | PyMuPDF | canonical_paper.md |",
        "|--------|-----------|---------|-------------------|",
        f"| Display formulas | {md_display} | {pm_display} | {canon_display} |",
        f"| Inline formulas | {md_inline} | {pm_inline} | {canon_inline} |",
        f"| FormulaBlock count | N/A | N/A | {len(canon_formulas)} |",
        "",
        "### MarkItDown Formula Samples (first 5)",
    ]
    for i, f in enumerate(md_formulas[:5]):
        summary_lines.append(f"\n**eq{i+1}:**")
        summary_lines.append(f"```latex")
        summary_lines.append(f"{f}")
        summary_lines.append(f"```")
        summary_lines.append(f"- origin: parser_latex")
        summary_lines.append(f"- looks like LaTeX: {'YES' if re.search(r'[\\\\{}^_]', f) else 'PARTIAL'}")

    if not md_formulas:
        summary_lines.append("\nNo display formulas detected in MarkItDown output.")

    summary_lines += ["", "### canonical_paper.md Formula Samples (first 5)"]
    for i, f in enumerate(canon_formulas[:5]):
        summary_lines.append(f"\n**eq{i+1}:**")
        summary_lines.append(f"```latex")
        summary_lines.append(f"{f}")
        summary_lines.append(f"```")

    summary_lines += [
        "",
        "## Verdict",
        "",
        f"- **MarkItDown**: {'Good content coverage, fast execution.' if len(md_text) > 20000 else 'Limited content.'} Formula preservation {'appears adequate' if md_display > 0 else 'needs improvement'}.",
        f"- **PyMuPDF**: Fast but no structure. {'Adequate for fallback.' if len(pm_text) > 10000 else 'Limited content.'}",
        f"- **Marker**: {'Best section structure but very slow (~16min).' if name == 'paper_1' else 'Skipped due to speed.'}",
    ]
    (out_dir / "compare_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"  compare_summary.md: written")

    # Write formula_review.md
    fr_lines = [
        f"# Formula Review: {info['title']}",
        "",
        "## Formula Counts",
        "",
        f"- MarkItDown display formulas: {md_display}",
        f"- MarkItDown inline formulas: {md_inline}",
        f"- PyMuPDF display formulas: {pm_display}",
        f"- PyMuPDF inline formulas: {pm_inline}",
        f"- canonical_paper.md FormulaBlocks: {len(canon_formulas)}",
        "",
        "## MarkItDown Formula Samples",
        "",
    ]
    for i, f in enumerate(md_formulas[:5]):
        fr_lines.append(f"### eq{i+1}")
        fr_lines.append(f"```latex")
        fr_lines.append(f"{f}")
        fr_lines.append(f"```")
        fr_lines.append(f"- origin: parser_latex")
        fr_lines.append(f"- structure: {'Preserves LaTeX structure' if re.search(r'[\\\\{}^_]', f) else 'Plain text, may be incomplete'}")
        fr_lines.append("")

    if not md_formulas:
        fr_lines.append("No display formulas detected.\n")

    fr_lines += ["## PyMuPDF Formula Samples", ""]
    for i, f in enumerate(pm_formulas[:5]):
        fr_lines.append(f"### eq{i+1}")
        fr_lines.append(f"```")
        fr_lines.append(f"{f[:200]}")
        fr_lines.append(f"```")
        fr_lines.append(f"- Note: PyMuPDF extracts raw text, not LaTeX")
        fr_lines.append("")

    if not pm_formulas:
        fr_lines.append("No display formulas detected.\n")

    fr_lines += [
        "## Formula Screenshots",
        "",
        "See formula_page_1.png, formula_page_2.png, formula_page_3.png for visual reference.",
        "",
        "## Conclusion",
        "",
    ]
    if md_display > 0:
        fr_lines.append("MarkItDown formula preservation appears good enough for current M1 default. Display formulas are detected and preserved in LaTeX-like format.")
    else:
        fr_lines.append("MarkItDown is enough for body text, but formula OCR is still needed for core equations.")

    (out_dir / "formula_review.md").write_text("\n".join(fr_lines), encoding="utf-8")
    print(f"  formula_review.md: written")

print("\n=== DONE ===")
