"""Build the M1 parser review HTML page."""
from pathlib import Path
import re
import html as html_mod

BASE = Path("reports/m1_parser_review")

PAPERS = [
    {
        "dir": "paper_1",
        "title": "Monte Carlo EM for Deep Time Series Anomaly Detection",
        "pid": "2112.14436",
    },
    {
        "dir": "paper_2",
        "title": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
        "pid": "W3184127157",
    },
    {
        "dir": "paper_3",
        "title": "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy",
        "pid": "W3204263062",
    },
]


def read_file(path, max_lines=None):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        if max_lines:
            lines = text.split("\n")
            return "\n".join(lines[:max_lines])
        return text
    except Exception as e:
        return f"[ERROR reading {path}: {e}]"


def count_sections(text):
    return len(re.findall(r"^#{1,3}\s+", text, re.MULTILINE))


def has_abstract(text):
    return "abstract" in text[:3000].lower()


def has_section(text, name):
    return name.lower() in text.lower()


def count_formulas(text):
    display = len(re.findall(r"\$\$.*?\$\$|\\begin\{equation", text, re.DOTALL))
    inline = len(re.findall(r"\$[^$]+\$", text))
    return display, inline


def build_parser_table(paper_dir):
    files = {
        "MarkItDown": paper_dir / "markitdown.md",
        "PyMuPDF": paper_dir / "pymupdf.txt",
        "Marker": paper_dir / "marker.md",
    }
    rows = []
    for parser_name, fpath in files.items():
        if not fpath.exists():
            if (paper_dir / "marker_skipped.txt").exists() and parser_name == "Marker":
                rows.append(f"<tr><td>{parser_name}</td><td colspan='9'>SKIPPED (too slow, ~16min/paper)</td></tr>")
            elif (paper_dir / "marker_failed.txt").exists() and parser_name == "Marker":
                rows.append(f"<tr><td>{parser_name}</td><td colspan='9'>FAILED</td></tr>")
            continue
        text = read_file(fpath)
        display, inline = count_formulas(text)
        secs = count_sections(text)
        rows.append(
            f"<tr>"
            f"<td>{parser_name}</td>"
            f"<td>-</td>"
            f"<td>{len(text):,}</td>"
            f"<td>{secs}</td>"
            f"<td>{'Y' if has_abstract(text) else 'N'}</td>"
            f"<td>{'Y' if has_section(text, 'introduction') else 'N'}</td>"
            f"<td>{'Y' if has_section(text, 'method') or has_section(text, 'approach') else 'N'}</td>"
            f"<td>{'Y' if has_section(text, 'experiment') or has_section(text, 'evaluation') else 'N'}</td>"
            f"<td>{'Y' if has_section(text, 'reference') else 'N'}</td>"
            f"<td>{display + inline}</td>"
            f"<td></td>"
            f"</tr>"
        )
    return "\n".join(rows)


def build_formula_table(paper_dir):
    md_text = read_file(paper_dir / "markitdown.md")
    formulas = re.findall(r"\$\$(.*?)\$\$", md_text, re.DOTALL)
    if not formulas:
        formulas = re.findall(r"\\begin\{equation\}(.*?)\\end\{equation\}", md_text, re.DOTALL)

    rows = []
    for i, f in enumerate(formulas[:10]):
        f_html = html_mod.escape(f.strip()[:200])
        has_latex = bool(re.search(r"[\\{}^_]", f))
        rows.append(
            f"<tr>"
            f"<td>eq{i+1}</td>"
            f"<td><pre>{f_html}</pre></td>"
            f"<td>{'YES' if has_latex else 'NO'}</td>"
            f"<td>{'Looks like LaTeX' if has_latex else 'Plain text, not LaTeX'}</td>"
            f"</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='4'>No display formulas detected in MarkItDown output</td></tr>")
    return "\n".join(rows)


def build_ocr_table(paper_dir):
    result_path = paper_dir.parent / "pix2tex_result.md"
    if not result_path.exists():
        return "<tr><td colspan='4'>pix2tex_result.md not found</td></tr>"

    text = read_file(result_path)
    # Extract OCR result
    match = re.search(r"```\n(.*?)\n```", text, re.DOTALL)
    ocr_output = match.group(1).strip() if match else "N/A"

    rows = []
    for i in range(1, 4):
        img_path = paper_dir / f"formula_page_{i}.png"
        if img_path.exists():
            ocr_html = html_mod.escape(ocr_output[:200]) if i == 1 else "N/A (same model)"
            looks_latex = "YES" if i == 1 and re.search(r"[\\{}]", ocr_output) else "N/A"
            rows.append(
                f"<tr>"
                f"<td><img src='{paper_dir.name}/formula_page_{i}.png' style='max-width:400px'></td>"
                f"<td><pre>{ocr_html}</pre></td>"
                f"<td>{looks_latex}</td>"
                f"<td>Structure OK but content inaccurate</td>"
                f"</tr>"
            )
    if not rows:
        rows.append("<tr><td colspan='4'>No formula screenshots found</td></tr>")
    return "\n".join(rows)


def build_paper_section(paper):
    paper_dir = BASE / paper["dir"]

    # File paths
    source_pdf = paper_dir / "source.pdf"
    markitdown_md = paper_dir / "markitdown.md"
    canonical_md = paper_dir / "canonical_paper.md"
    marker_md = paper_dir / "marker.md"
    pymupdf_txt = paper_dir / "pymupdf.txt"

    # MarkItDown preview (first 200 lines)
    md_preview = html_mod.escape(read_file(markitdown_md, max_lines=200))

    # Canonical preview (front matter + first 200 lines)
    canon_text = read_file(canonical_md, max_lines=200)
    canon_preview = html_mod.escape(canon_text)

    # Parser comparison table
    parser_table = build_parser_table(paper_dir)

    # Formula table
    formula_table = build_formula_table(paper_dir)

    # OCR table
    ocr_table = build_ocr_table(paper_dir)

    # Page images
    page_imgs = ""
    for i in range(1, 4):
        img = paper_dir / f"page_{i}.png"
        if img.exists():
            page_imgs += f"<img src='{paper['dir']}/page_{i}.png' style='max-width:400px; margin:5px'>"

    # Formula page images
    formula_imgs = ""
    for i in range(1, 4):
        img = paper_dir / f"formula_page_{i}.png"
        if img.exists():
            formula_imgs += f"<img src='{paper['dir']}/formula_page_{i}.png' style='max-width:400px; margin:5px'>"

    return f"""
    <section class="paper">
      <h2>{html_mod.escape(paper['title'])}</h2>
      <p><strong>paper_id:</strong> {paper['pid']}</p>

      <h3>File Paths</h3>
      <ul>
        <li>source.pdf: <code>{source_pdf.resolve()}</code></li>
        <li>markitdown.md: <code>{markitdown_md.resolve()}</code></li>
        <li>canonical_paper.md: <code>{canonical_md.resolve()}</code></li>
        <li>marker.md: <code>{marker_md.resolve() if marker_md.exists() else 'N/A'}</code></li>
        <li>pymupdf.txt: <code>{pymupdf_txt.resolve()}</code></li>
      </ul>

      <h3>Parser Comparison</h3>
      <table>
        <tr><th>Parser</th><th>Time</th><th>Chars</th><th>Sections</th><th>Abstract</th><th>Intro</th><th>Method</th><th>Experiments</th><th>Refs</th><th>Formulas</th><th>Notes</th></tr>
        {parser_table}
      </table>

      <h3>PDF Page Screenshots</h3>
      <div class="images">{page_imgs}</div>

      <h3>Formula Page Screenshots</h3>
      <div class="images">{formula_imgs}</div>

      <h3>Formula Analysis (MarkItDown)</h3>
      <table>
        <tr><th>ID</th><th>LaTeX</th><th>Is LaTeX?</th><th>Assessment</th></tr>
        {formula_table}
      </table>

      <h3>pix2tex OCR Test</h3>
      <table>
        <tr><th>Formula Image</th><th>OCR Output</th><th>Looks Like LaTeX?</th><th>Assessment</th></tr>
        {ocr_table}
      </table>

      <h3>MarkItDown Output (first 200 lines)</h3>
      <pre class="preview">{md_preview}</pre>

      <h3>canonical_paper.md (first 200 lines)</h3>
      <pre class="preview">{canon_preview}</pre>
    </section>
    """


# Build HTML
paper_sections = "\n".join(build_paper_section(p) for p in PAPERS)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>M1 Parser Review</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
  .verdict {{ background: #1a1a2e; color: #fff; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
  .verdict h2 {{ color: #e94560; margin-top: 0; }}
  .verdict table {{ width: 100%; border-collapse: collapse; }}
  .verdict td {{ padding: 8px; border-bottom: 1px solid #333; }}
  .verdict td:first-child {{ font-weight: bold; width: 300px; }}
  .yes {{ color: #0f0; font-weight: bold; }}
  .no {{ color: #f00; font-weight: bold; }}
  .borderline {{ color: #ff0; font-weight: bold; }}
  .review {{ color: #ff0; font-weight: bold; }}
  .paper {{ background: #fff; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .paper h2 {{ color: #16213e; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
  .paper h3 {{ color: #0f3460; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }}
  th {{ background: #16213e; color: #fff; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .preview {{ background: #1a1a2e; color: #a8e6cf; padding: 15px; border-radius: 4px; overflow-x: auto; max-height: 500px; overflow-y: auto; font-size: 12px; line-height: 1.4; }}
  .images {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .images img {{ border: 1px solid #ddd; border-radius: 4px; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; }}
  code {{ background: #eee; padding: 2px 4px; border-radius: 2px; font-size: 12px; }}
  ul {{ font-size: 13px; }}
  li {{ margin-bottom: 4px; }}
</style>
</head>
<body>

<div class="verdict">
  <h2>M1 Parser Review - Conclusions</h2>
  <table>
    <tr><td>MarkItDown 正文是否可用</td><td class="yes">YES</td></tr>
    <tr><td>MarkItDown 公式是否可用</td><td class="no">NO</td></tr>
    <tr><td>canonical_paper.md 是否可读</td><td class="yes">YES</td></tr>
    <tr><td>pix2tex 是否建议进入 M1</td><td class="borderline">ON_DEMAND_LOW_CONFIDENCE</td></tr>
    <tr><td>M1 是否可收口</td><td class="review">NEED_USER_REVIEW</td></tr>
  </table>
  <p style="margin-top:15px;color:#aaa;">请查看下方 3 篇论文的详细对比，然后决定 M1 是否可以收口。</p>
</div>

{paper_sections}

</body>
</html>"""

(BASE / "index.html").write_text(html_content, encoding="utf-8")
print("index.html generated")
