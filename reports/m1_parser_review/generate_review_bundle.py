"""Generate the M1 parser review bundle for the three live-eval papers."""
from __future__ import annotations

import json
import shutil
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.canonical.material_normalizer import MaterialNormalizer
from researchsensei.canonical.parser_quality import (
    ParserQualityScore,
    extract_formula_candidates,
    formula_text_matches,
    score_parser_output,
    select_best_parser,
)
from researchsensei.schemas.canonical import CanonicalPaper, CanonicalPaperFrontMatter, FormulaBlock
from researchsensei.schemas.enums import (
    CanonicalQualityStatus,
    CanonicalizationStatus,
    FormulaOcrStatus,
    FormulaOrigin,
)


PAPERS = {
    "paper_1": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/2112.14436/source.pdf",
        "pid": "2112.14436",
        "title": "Monte Carlo EM for Deep Time Series Anomaly Detection",
        "core_formulas": [
            "p(x|z)",
            "p(xt|zt=0)",
            "p(zt+1|zt)",
            "ELBO",
            "Monte Carlo EM",
        ],
        "marker_policy": "review_cached_or_timeout",
    },
    "paper_2": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/W3184127157/source.pdf",
        "pid": "W3184127157",
        "title": "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT",
        "core_formulas": [
            "Gumbel-softmax",
            "Attention(Q,K,V)",
            "MultiHead(Q,K,V)",
            "graph convolution",
            "Influence Propagation",
        ],
        "marker_policy": "skipped_by_policy",
    },
    "paper_3": {
        "src": "reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/2510.18998/source.pdf",
        "pid": "2510.18998",
        "title": "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection",
        "core_formulas": [
            "Prior-Association",
            "Series-Association",
            "AssDis(P,S;X)",
            "AnomalyScore(X)",
            "mutual information",
        ],
        "marker_policy": "skipped_by_policy",
    },
}


BASE = ROOT / "reports" / "m1_parser_review"
LIVE_EVAL_DIR = ROOT / "reports" / "live_eval" / "work" / "m1" / "workspace" / "runs" / "m1-live"
MARKER_TIMEOUT_SECONDS = 90.0
STANDARD_SECTIONS = ["Abstract", "Introduction", "Method", "Experiments", "Conclusion", "References"]


def run_markitdown(pdf_path: Path) -> tuple[str, float, str]:
    import time

    try:
        from markitdown import MarkItDown

        t0 = time.time()
        text = MarkItDown(enable_plugins=False).convert(str(pdf_path)).text_content
        return text, time.time() - t0, "completed"
    except Exception as exc:
        return "", 0.0, f"failed: {type(exc).__name__}: {exc}"


def run_pymupdf(pdf_path: Path) -> tuple[str, float, str]:
    import time

    try:
        import fitz

        t0 = time.time()
        with fitz.open(str(pdf_path)) as doc:
            text = "\n".join(page.get_text() for page in doc)
        return text, time.time() - t0, "completed"
    except Exception as exc:
        return "", 0.0, f"failed: {type(exc).__name__}: {exc}"


def load_or_run_marker(pdf_path: Path, out_dir: Path, paper_name: str) -> tuple[str | None, float, str]:
    if paper_name != "paper_1":
        skipped = (
            "marker_status=skipped_by_policy\n"
            "marker_enabled=false\n"
            "trigger_mode=never\n"
            f"timeout_seconds={MARKER_TIMEOUT_SECONDS}\n"
            "ordinary live eval does not run Marker; review bundle keeps Marker disabled for this paper.\n"
        )
        (out_dir / "marker_skipped_by_policy.txt").write_text(skipped, encoding="utf-8")
        return None, 0.0, "skipped_by_policy"

    cached = out_dir / "marker.md"
    if cached.exists() and cached.read_text(encoding="utf-8", errors="ignore").strip():
        return cached.read_text(encoding="utf-8", errors="ignore"), 0.0, "completed_from_cache"

    normalizer = MaterialNormalizer(
        marker_enabled=True,
        marker_trigger_mode="review",
        marker_timeout_seconds=MARKER_TIMEOUT_SECONDS,
    )
    t0 = time.time()
    text, warning = normalizer._run_marker_with_timeout(pdf_path, MARKER_TIMEOUT_SECONDS)
    elapsed = time.time() - t0
    if text:
        (out_dir / "marker.md").write_text(text, encoding="utf-8")
        return text, elapsed, "completed"

    failure = (
        "marker_status=timeout_degraded\n"
        "marker_enabled=true\n"
        "trigger_mode=review\n"
        f"timeout_seconds={MARKER_TIMEOUT_SECONDS}\n"
        f"reason={warning or 'Marker returned no markdown'}\n"
    )
    (out_dir / "marker_timeout_or_failed.txt").write_text(failure, encoding="utf-8")
    return None, elapsed, warning or "timeout_degraded"


def skipped_marker_score(reason: str) -> ParserQualityScore:
    return ParserQualityScore(
        parser_name="marker_pdf",
        output_length=0,
        section_count=0,
        long_concat_count=0,
        spacing_quality=1.0,
        formula_candidate_count=0,
        cid_token_count=0,
        garbled_line_ratio=0.0,
        overall_score=0.0,
        selection_reason=reason,
    )


def score_to_dict(score: ParserQualityScore) -> dict[str, object]:
    return {
        "overall_score": round(score.overall_score, 1),
        "output_length": score.output_length,
        "section_count": score.section_count,
        "long_concat_count": score.long_concat_count,
        "spacing_quality": round(score.spacing_quality, 3),
        "cid_token_count": score.cid_token_count,
        "formula_candidate_count": score.formula_candidate_count,
        "garbled_line_ratio": round(score.garbled_line_ratio, 3),
        "reason": score.selection_reason or "scored",
    }


def build_canonical(
    info: dict,
    md_text: str,
    pm_text: str,
    marker_text: str | None,
) -> tuple[str, list[FormulaBlock], list[dict], list[ParserQualityScore], str, CanonicalQualityStatus, str]:
    selection = select_best_parser(md_text, pm_text, marker_text)
    normalizer = MaterialNormalizer(marker_enabled=False)
    normalizer._last_parser_used = selection.selected_parser
    normalizer._parser_quality_scores = selection.candidates
    selected_score = next(score for score in selection.candidates if score.parser_name == selection.selected_parser)
    normalizer._selected_parser_score = selected_score.overall_score
    normalizer._parser_selection_reason = selection.selection_reason
    normalizer._parser_quality_details = {score.parser_name: score_to_dict(score) for score in selection.candidates}

    sections = normalizer._parse_text_sections(selection.selected_text, info["title"])
    sections, quality_status, quality_reasons = normalizer._repair_and_assess_sections(sections)

    formula_blocks: list[FormulaBlock] = []
    formula_rows: list[dict] = []
    for index, candidate in enumerate(selection.formula_candidates, start=1):
        origin = FormulaOrigin(candidate["origin"])
        latex = candidate.get("latex", "") if origin != FormulaOrigin.RAW_FORMULA_TEXT else ""
        raw_formula_text = candidate.get("raw_formula_text", "") if origin == FormulaOrigin.RAW_FORMULA_TEXT else ""
        block = FormulaBlock(
            formula_id=f"fc_{index}",
            latex=latex,
            raw_formula_text=raw_formula_text,
            is_latex=bool(candidate.get("is_latex", False)) and origin != FormulaOrigin.RAW_FORMULA_TEXT,
            confidence=float(candidate.get("confidence", 0.0)),
            origin=origin,
            section="Formula Blocks",
            ocr_status=FormulaOcrStatus.NOT_TRIGGERED,
        )
        formula_blocks.append(block)
        formula_rows.append(
            {
                "formula_id": block.formula_id,
                "origin": block.origin.value,
                "is_latex": block.is_latex,
                "confidence": block.confidence,
                "source_parser": candidate.get("source", "unknown"),
                "content": block.latex or block.raw_formula_text,
            }
        )

    canonical_status = (
        CanonicalizationStatus.FAILED
        if quality_status == CanonicalQualityStatus.FAIL
        else CanonicalizationStatus.DEGRADED
        if quality_status == CanonicalQualityStatus.DEGRADED
        else CanonicalizationStatus.SUCCESS
    )
    degradation_reason = "; ".join(quality_reasons)
    quality_details = {score.parser_name: score_to_dict(score) for score in selection.candidates}
    front_matter = CanonicalPaperFrontMatter(
        paper_id=info["pid"],
        title=info["title"],
        source_type="PDF",
        source_confidence="medium",
        canonicalization_status=canonical_status,
        canonical_quality_status=quality_status,
        parser_used=selection.selected_parser,
        m2_ready=quality_status != CanonicalQualityStatus.FAIL,
        degradation_reason=degradation_reason,
        parser_candidates=[score.parser_name for score in selection.candidates],
        selected_parser=selection.selected_parser,
        parser_quality_score=selected_score.overall_score,
        parser_selection_reason=selection.selection_reason,
        parser_quality_details_json=json.dumps(quality_details, ensure_ascii=False),
    )
    canonical = CanonicalPaper(front_matter=front_matter, sections=sections, formula_blocks=formula_blocks)
    return (
        normalizer._render_markdown(canonical),
        formula_blocks,
        formula_rows,
        selection.candidates,
        selection.selected_parser,
        quality_status,
        degradation_reason,
    )


def parser_texts(md_text: str, pm_text: str, marker_text: str | None) -> list[tuple[str, str]]:
    texts = [("markitdown", md_text), ("pymupdf", pm_text)]
    if marker_text:
        texts.append(("marker", marker_text))
    return texts


def formula_content(block: FormulaBlock) -> str:
    return block.latex if block.origin != FormulaOrigin.RAW_FORMULA_TEXT else block.raw_formula_text


def coverage_status(query: str, blocks: list[FormulaBlock], canonical_text: str, texts: list[tuple[str, str]]) -> str:
    for block in blocks:
        if block.origin != FormulaOrigin.RAW_FORMULA_TEXT and formula_text_matches(query, formula_content(block)):
            return "FOUND_LATEX"
    for block in blocks:
        if block.origin == FormulaOrigin.RAW_FORMULA_TEXT and formula_text_matches(query, formula_content(block)):
            return "FOUND_RAW_TEXT"
    if formula_text_matches(query, canonical_text):
        return "FOUND_TEXT"
    for parser_name, text in texts:
        if formula_text_matches(query, text):
            return f"MISSING_CANONICAL: present in {parser_name} parser text but not promoted to FormulaBlock"
    return "MISSING: not present in MarkItDown, PyMuPDF, Marker, or canonical text"


def extract_section(canon_text: str, section_name: str, max_chars: int = 1000) -> str:
    marker = f"## {section_name}"
    start = canon_text.find(marker)
    if start < 0:
        return "missing"
    start = canon_text.find("\n", start)
    if start < 0:
        return "missing"
    next_start = canon_text.find("\n## ", start + 1)
    content = canon_text[start: next_start if next_start >= 0 else len(canon_text)].strip()
    if content.startswith("<!--"):
        return "missing"
    return content[:max_chars] if content else "missing"


def generate_compare_summary(
    info: dict,
    md_text: str,
    pm_text: str,
    marker_text: str | None,
    scores: list[ParserQualityScore],
    marker_score: ParserQualityScore,
    canon_text: str,
    selected_parser: str,
    quality_status: CanonicalQualityStatus,
    degradation_reason: str,
) -> str:
    by_name = {score.parser_name: score for score in scores}
    if "marker_pdf" not in by_name:
        by_name["marker_pdf"] = marker_score
    selected_score = by_name[selected_parser]
    lines = [
        f"# Parser Comparison: {info['title']}",
        "",
        "## Basic Info",
        f"- title: {info['title']}",
        f"- paper_id: {info['pid']}",
        f"- source_pdf_path: {info['src']}",
        f"- selected_parser: {selected_parser}",
        f"- parser_selection_reason: {selected_score.selection_reason or 'scored'}",
        f"- parser_quality_score: {selected_score.overall_score:.1f}",
        f"- canonical_quality_status: {quality_status.value}",
        f"- degradation_reason: {degradation_reason or 'none'}",
        f"- canonical_paper_path: reports/m1_parser_review/{info.get('bundle_dir', info['pid'])}/canonical_paper.md",
        "",
        "## Parser Quality Table",
        "",
        "| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |",
        "| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |",
    ]
    for name in ("markitdown_pdf", "pymupdf", "marker_pdf"):
        score = by_name[name]
        selected = "YES" if name == selected_parser else "NO"
        reason = (score.selection_reason or "scored").replace("|", "/")
        lines.append(
            f"| {name} | {score.overall_score:.1f} | {score.output_length} | {score.section_count} | "
            f"{score.long_concat_count} | {score.spacing_quality:.3f} | {score.cid_token_count} | "
            f"{score.formula_candidate_count} | {score.garbled_line_ratio:.3f} | {selected} | {reason} |"
        )

    excerpt_len = 900
    lines += [
        "",
        "## Text Excerpt Comparison",
        "",
        "### MarkItDown Excerpt",
        "```text",
        md_text[:excerpt_len] or "empty",
        "```",
        "",
        "### PyMuPDF Excerpt",
        "```text",
        pm_text[:excerpt_len] or "empty",
        "```",
        "",
        "### Marker Excerpt",
        "```text",
        (marker_text or "marker skipped by policy")[:excerpt_len],
        "```",
        "",
        "### Selected Canonical Excerpt",
        "```text",
        canon_text[:excerpt_len] or "empty",
        "```",
    ]
    return "\n".join(lines)


def generate_formula_review(
    info: dict,
    formula_rows: list[dict],
    formula_blocks: list[FormulaBlock],
    canon_text: str,
    texts: list[tuple[str, str]],
) -> str:
    counts = {
        "source_latex": 0,
        "parser_latex": 0,
        "ocr_latex": 0,
        "raw_formula_text": 0,
        "unknown": 0,
    }
    for block in formula_blocks:
        counts[block.origin.value if block.origin.value in counts else "unknown"] += 1

    lines = [
        f"# Formula Review: {info['title']}",
        "",
        "## Formula Statistics",
        "",
        "| type | count |",
        "| ---- | ----: |",
    ]
    for origin, count in counts.items():
        lines.append(f"| {origin} | {count} |")
    lines.append(f"| canonical FormulaBlock total | {len(formula_blocks)} |")

    lines += [
        "",
        "## Formula Samples (from canonical paper)",
        "",
        "| id | origin | is_latex | confidence | source_parser | content |",
        "| -- | ------ | -------- | ---------: | ------------- | ------- |",
    ]
    for row in formula_rows[:15]:
        content = row["content"][:120].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {row['formula_id']} | {row['origin']} | {row['is_latex']} | "
            f"{row['confidence']:.2f} | {row['source_parser']} | {content} |"
        )

    lines += ["", "## Core Formula Coverage", ""]
    for query in info["core_formulas"]:
        lines.append(f"- {query}: {coverage_status(query, formula_blocks, canon_text, texts)}")

    lines += [
        "",
        "## Raw Formula Text Check",
        "",
    ]
    raw_rows = [row for row in formula_rows if row["origin"] == FormulaOrigin.RAW_FORMULA_TEXT.value]
    if not raw_rows:
        lines.append("No raw_formula_text blocks were generated.")
    for row in raw_rows:
        if row["is_latex"]:
            lines.append(f"WARNING: {row['formula_id']} has origin=raw_formula_text but is_latex=True")
        else:
            lines.append(f"OK: {row['formula_id']} uses raw_formula_text and leaves latex empty")
    return "\n".join(lines)


def generate_section_samples(canon_text: str, info: dict) -> str:
    lines = [f"# Section Samples: {info['title']}", ""]
    for section in STANDARD_SECTIONS:
        content = extract_section(canon_text, section)
        lines += [f"## {section} sample", ""]
        if content == "missing":
            lines += [
                "missing",
                "",
                "Reason: section is absent or empty after canonical repair.",
            ]
        else:
            lines.append(content)
        lines.append("")
    return "\n".join(lines)


def generate_formula_candidates(
    info: dict,
    md_text: str,
    pm_text: str,
    marker_text: str | None,
    selected_parser: str,
) -> str:
    candidates = extract_formula_candidates(selected_parser, md_text, pm_text, marker_text)
    lines = [
        f"# Formula Candidates: {info['title']}",
        "",
        "| idx | source_parser | origin | is_latex | confidence | content |",
        "| --: | ------------- | ------ | -------- | ---------: | ------- |",
    ]
    for idx, candidate in enumerate(candidates, start=1):
        content = (candidate.get("latex") or candidate.get("raw_formula_text") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {idx} | {candidate.get('source', 'unknown')} | {candidate.get('origin', 'unknown')} | "
            f"{candidate.get('is_latex', False)} | {float(candidate.get('confidence', 0.0)):.2f} | {content[:180]} |"
        )
    if not candidates:
        lines.append("| 0 | none | none | False | 0.00 | no candidates |")
    return "\n".join(lines)


def generate_formula_dense_pages(pdf_path: Path, info: dict, pages: list[dict]) -> str:
    selected_pages = {page["page"] for page in pages[:5]}
    lines = [
        f"# Formula Dense Pages: {info['title']}",
        "",
        "Detected from PyMuPDF PDF page text, not from selected parser text.",
        "",
        "| page | math_token_count | density | selected | sample_lines |",
        "| ---: | ---------------: | ------: | -------- | ------------ |",
    ]
    for page in pages:
        sample = " / ".join(page.get("sample_lines", [])[:2]) or "none"
        sample = sample.replace("|", "\\|")[:160]
        selected = "YES" if page["page"] in selected_pages else "NO"
        lines.append(
            f"| {page['page']} | {page['math_token_count']} | {page['density']} | {selected} | {sample} |"
        )
    if not pages:
        lines.append("| 0 | 0 | 0.0 | NO | no PDF text pages scanned |")
    return "\n".join(lines)


def save_formula_page_screenshots(pdf_path: Path, out_dir: Path, pages: list[dict]) -> None:
    try:
        import fitz

        with fitz.open(str(pdf_path)) as doc:
            for page in pages[:3]:
                page_num = int(page["page"])
                if 1 <= page_num <= len(doc):
                    pix = doc[page_num - 1].get_pixmap(dpi=150)
                    pix.save(str(out_dir / f"formula_page_{page_num}.png"))
    except Exception as exc:
        (out_dir / "formula_page_screenshot_error.txt").write_text(str(exc), encoding="utf-8")


def write_readme(started_at: float, results: list[dict]) -> None:
    lines = [
        "# M1 Parser Review Bundle",
        "",
        "This bundle is generated for M1 canonical parser review only. It excludes reports from git.",
        "",
        "Marker policy: ordinary live eval keeps marker_enabled=false with trigger_mode=never. The review bundle may use cached Marker output for paper_1; paper_2 and paper_3 include skipped_by_policy files.",
        "",
        "| paper | selected_parser | parser_score | canonical_quality_status | m2_ready | reason |",
        "| ----- | --------------- | -----------: | ------------------------ | -------- | ------ |",
    ]
    for item in results:
        lines.append(
            f"| {item['paper']} | {item['selected_parser']} | {item['score']:.1f} | "
            f"{item['quality']} | {item['m2_ready']} | {item['reason'].replace('|', '/')} |"
        )
    lines += [
        "",
        f"Generated in {time.time() - started_at:.1f}s.",
    ]
    (BASE / "README_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def zip_bundle() -> Path:
    zip_path = BASE / "m1_parser_review_bundle.zip"
    if zip_path.exists():
        zip_path.unlink()
    include_roots = [BASE / name for name in PAPERS] + [BASE / "README_REVIEW.md"]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root in include_roots:
            if root.is_file():
                zf.write(root, root.relative_to(BASE))
            elif root.is_dir():
                for path in root.rglob("*"):
                    if path.is_file():
                        zf.write(path, path.relative_to(BASE))
    return zip_path


def main() -> None:
    started_at = time.time()
    BASE.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for paper_name, raw_info in PAPERS.items():
        info = dict(raw_info)
        info["bundle_dir"] = paper_name
        print(f"\n=== {paper_name}: {info['title']} ===")
        pdf_path = ROOT / info["src"]
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

        out_dir = BASE / paper_name
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, out_dir / "source.pdf")

        md_text, md_time, md_status = run_markitdown(pdf_path)
        (out_dir / "markitdown.md").write_text(md_text or f"FAILED: {md_status}", encoding="utf-8")
        pm_text, pm_time, pm_status = run_pymupdf(pdf_path)
        (out_dir / "pymupdf.txt").write_text(pm_text or f"FAILED: {pm_status}", encoding="utf-8")
        marker_text, marker_time, marker_status = load_or_run_marker(pdf_path, out_dir, paper_name)

        md_score = score_parser_output(md_text, "markitdown_pdf")
        pm_score = score_parser_output(pm_text, "pymupdf")
        marker_score = score_parser_output(marker_text, "marker_pdf") if marker_text else skipped_marker_score(marker_status)
        canon_text, formula_blocks, formula_rows, scores, selected_parser, quality_status, degradation_reason = build_canonical(
            info,
            md_text,
            pm_text,
            marker_text,
        )
        (out_dir / "canonical_paper.md").write_text(canon_text, encoding="utf-8")

        by_name = {score.parser_name: score for score in scores}
        selected_score = by_name[selected_parser]
        (out_dir / "compare_summary.md").write_text(
            generate_compare_summary(
                info,
                md_text,
                pm_text,
                marker_text,
                scores,
                marker_score,
                canon_text,
                selected_parser,
                quality_status,
                degradation_reason,
            ),
            encoding="utf-8",
        )
        texts = parser_texts(md_text, pm_text, marker_text)
        (out_dir / "formula_review.md").write_text(
            generate_formula_review(info, formula_rows, formula_blocks, canon_text, texts),
            encoding="utf-8",
        )
        (out_dir / "section_samples.md").write_text(generate_section_samples(canon_text, info), encoding="utf-8")
        (out_dir / "formula_candidates.md").write_text(
            generate_formula_candidates(info, md_text, pm_text, marker_text, selected_parser),
            encoding="utf-8",
        )

        dense_pages = MaterialNormalizer().find_formula_dense_pages_from_pdf(pdf_path)
        (out_dir / "formula_dense_pages.md").write_text(
            generate_formula_dense_pages(pdf_path, info, dense_pages),
            encoding="utf-8",
        )
        save_formula_page_screenshots(pdf_path, out_dir, dense_pages)

        if marker_text:
            (out_dir / "marker.md").write_text(marker_text, encoding="utf-8")

        results.append(
            {
                "paper": paper_name,
                "selected_parser": selected_parser,
                "score": selected_score.overall_score,
                "quality": quality_status.value,
                "m2_ready": quality_status != CanonicalQualityStatus.FAIL,
                "reason": degradation_reason or selected_score.selection_reason or "scored",
                "md_time": md_time,
                "pm_time": pm_time,
                "marker_time": marker_time,
                "marker_status": marker_status,
            }
        )
        print(f"selected_parser={selected_parser} score={selected_score.overall_score:.1f}")
        print(f"canonical_quality_status={quality_status.value} reason={degradation_reason or 'none'}")
        print(f"formula_blocks={len(formula_blocks)} marker_status={marker_status}")

    write_readme(started_at, results)
    zip_path = zip_bundle()
    print(f"\nWrote {zip_path}")


if __name__ == "__main__":
    main()
