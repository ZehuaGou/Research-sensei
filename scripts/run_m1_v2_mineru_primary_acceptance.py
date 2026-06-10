from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import arxiv
import fitz
import httpx
from PIL import Image

from researchsensei.canonical.document_blocks import CanonicalDocumentBlock
from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter
from researchsensei.canonical.pipeline_v2 import M1V2CanonicalPipeline


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "m1_v2_mineru_primary_acceptance"
KNOWN_PAPER_RE = re.compile(
    r"monte carlo em|learning graph structures with transformer|anomaly transformer|memto|tranad",
    re.I,
)
REJECT_TITLE_RE = re.compile(r"survey|review|forecast|forecasting|classification|taxonomy|benchmarking", re.I)
THEME_RE = re.compile(r"transformer|diffusion|graph|attention", re.I)
FORMULA_LINE_RE = re.compile(
    r"(=|\\frac|\\sum|\\prod|\\arg|softmax|attention|\bL\s*=|\bx_\{|\bx_t|\bz_t|\bscore\b|\banomaly score\b|\bloss\b)",
    re.I,
)


@dataclass(frozen=True)
class Candidate:
    key: str
    title: str
    pdf_url: str
    published: str
    pages: int
    formula_like_lines: int
    query: str
    authors: list[str]
    local_pdf: Path


QUERIES = [
    "time series anomaly detection transformer",
    "multivariate time series anomaly detection transformer",
    "time series anomaly detection graph neural network",
    "time series anomaly detection diffusion model",
    "anomaly detection transformer sensor time series",
    "anomaly detection graph transformer time series",
]


DEFAULT_KEYS = ("2310_08800v2", "2312_01729v1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real MinerU2.5-Pro primary M1 v2 acceptance.")
    parser.add_argument("--limit", type=int, default=2, help="Number of selected unseen papers to run.")
    parser.add_argument("--keys", default=",".join(DEFAULT_KEYS), help="Comma-separated arXiv short IDs from the candidate pool.")
    parser.add_argument("--max-pages", type=int, default=0, help="Developer smoke limit. Acceptance must use 0.")
    parser.add_argument("--render-scale", type=float, default=1.0)
    parser.add_argument("--force", action="store_true", help="Ignore cached MinerU page JSON.")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    candidates = search_and_download_candidates(OUT / "_candidate_downloads")
    selected_keys = [item.strip() for item in args.keys.split(",") if item.strip()][: args.limit]
    selected = select_candidates(candidates, selected_keys)

    adapter = MinerU25ProAdapter(render_scale=args.render_scale)
    rows = []
    for candidate in selected:
        rows.append(run_candidate(candidate, adapter, max_pages=args.max_pages, force=args.force))
    write_top_level(candidates, rows, max_pages=args.max_pages)
    make_bundle()
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def search_and_download_candidates(download_dir: Path) -> list[Candidate]:
    download_dir.mkdir(parents=True, exist_ok=True)
    client = arxiv.Client(page_size=20, delay_seconds=1.0, num_retries=3)
    http = httpx.Client(timeout=60, follow_redirects=True)
    seen: set[str] = set()
    candidates: list[Candidate] = []
    for query in QUERIES:
        search = arxiv.Search(query=query, max_results=20, sort_by=arxiv.SortCriterion.Relevance)
        for result in client.results(search):
            title = " ".join(result.title.split())
            text = f"{title} {result.summary}"
            if result.entry_id in seen:
                continue
            if KNOWN_PAPER_RE.search(text) or REJECT_TITLE_RE.search(title):
                continue
            lowered = text.lower()
            if "anomaly" not in lowered or "time" not in lowered or "series" not in lowered:
                continue
            if not THEME_RE.search(text):
                continue
            key = result.get_short_id().replace("/", "_").replace(".", "_")
            pdf_path = download_dir / f"{key}.pdf"
            if not pdf_path.exists():
                response = http.get(result.pdf_url)
                response.raise_for_status()
                if "pdf" not in response.headers.get("content-type", "").lower() and not response.content.startswith(b"%PDF"):
                    continue
                pdf_path.write_bytes(response.content)
            pages, formula_like_lines = pdf_stats(pdf_path)
            candidate = Candidate(
                key=key,
                title=title,
                pdf_url=result.pdf_url,
                published=result.published.isoformat(),
                pages=pages,
                formula_like_lines=formula_like_lines,
                query=query,
                authors=[author.name for author in result.authors[:5]],
                local_pdf=pdf_path,
            )
            candidates.append(candidate)
            seen.add(result.entry_id)
    candidates = sorted(candidates, key=lambda item: item.formula_like_lines, reverse=True)
    (OUT / "candidate_search.json").write_text(
        json.dumps([candidate_to_json(item) for item in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return candidates


def select_candidates(candidates: list[Candidate], keys: list[str]) -> list[Candidate]:
    by_key = {candidate.key: candidate for candidate in candidates}
    selected = []
    for key in keys:
        if key not in by_key:
            raise RuntimeError(f"Selected key not found in candidate pool: {key}")
        selected.append(by_key[key])
    return selected


def run_candidate(
    candidate: Candidate,
    adapter: MinerU25ProAdapter,
    *,
    max_pages: int,
    force: bool,
) -> dict[str, Any]:
    paper_dir = OUT / candidate.key
    paper_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = paper_dir / "source.pdf"
    shutil.copy2(candidate.local_pdf, source_pdf)

    start = time.perf_counter()
    blocks, raw_payload = parse_with_mineru_cache(
        adapter,
        source_pdf,
        paper_dir,
        max_pages=max_pages,
        force=force,
    )
    (paper_dir / "raw_mineru_output.json").write_text(
        json.dumps(raw_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result = M1V2CanonicalPipeline(mineru_adapter=adapter).run_from_blocks(
        paper_id=candidate.key,
        title=candidate.title,
        blocks=blocks,
        output_dir=paper_dir,
        source_pdf_path=str(source_pdf),
        initial_metrics={
            "primary_parser": "mineru25pro",
            "mineru_available": True,
            "mineru_runtime_seconds": round(time.perf_counter() - start, 3),
            "mineru_raw_payload_pages": len(raw_payload["pages"]),
            "mineru_raw_payload_total_blocks": len(blocks),
            "acceptance_max_pages": max_pages,
        },
    )
    slots = json.loads((paper_dir / "formula_slots.json").read_text(encoding="utf-8"))
    canonical_text = Path(result.canonicalization.canonical_paper_path).read_text(encoding="utf-8")
    body_formula_count = sum(
        1
        for formula in result.canonicalization.formula_blocks
        if formula.section not in {"References", "Appendix"}
    )
    metrics = {
        "paper_key": candidate.key,
        "title": candidate.title,
        "primary_parser": "mineru25pro",
        "fallback_used": False,
        "title_ok": bool(candidate.title.strip()) and candidate.title.strip() in canonical_text,
        "quality_status": result.quality.status.value,
        "m2_ready": result.canonicalization.m2_ready,
        "formula_m2_ready": result.canonicalization.m2_ready_for_formula_understanding,
        "formula_count": len(result.canonicalization.formula_blocks),
        "body_formula_count": body_formula_count,
        "reference_formula_count": len(result.canonicalization.formula_blocks) - body_formula_count,
        "latex_count": sum(1 for formula in result.canonicalization.formula_blocks if formula.latex),
        "bbox_count": sum(1 for formula in result.canonicalization.formula_blocks if len(formula.bbox) == 4),
        "crop_count": sum(1 for slot in slots if slot.get("crop_path")),
        "overlay_count": sum(1 for slot in slots if slot.get("overlay_path")),
        "canonical_match_count": canonical_match_count(result.canonicalization.formula_blocks, canonical_text),
        "polluted_section_count": result.quality.polluted_section_count,
        "section_contradiction_count": result.quality.section_contradiction_count,
        "all_Abstract": result.quality.all_formulas_in_abstract_suspicious,
        "high_risk_count": result.quality.high_risk_count,
        "blocking_reasons": result.quality.blocking_reasons,
        "warning_reasons": result.quality.warning_reasons,
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "max_pages": max_pages,
    }
    metrics["acceptance_reasons"] = acceptance_reasons(metrics)
    metrics["status"] = "PASS" if not metrics["acceptance_reasons"] else "BLOCKED"
    (paper_dir / "acceptance_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (paper_dir / "README.md").write_text(render_paper_readme(candidate, metrics), encoding="utf-8")
    return metrics


def parse_with_mineru_cache(
    adapter: MinerU25ProAdapter,
    pdf_path: Path,
    output_dir: Path,
    *,
    max_pages: int,
    force: bool,
) -> tuple[list[CanonicalDocumentBlock], dict[str, Any]]:
    adapter.load()
    if adapter.client is None:
        raise RuntimeError("MinerU2.5-Pro client did not load")

    page_dir = output_dir / "raw_mineru_pages"
    page_dir.mkdir(parents=True, exist_ok=True)
    blocks: list[CanonicalDocumentBlock] = []
    raw_pages: list[dict[str, Any]] = []
    started = time.perf_counter()

    with fitz.open(str(pdf_path)) as doc:
        total_pages = len(doc) if max_pages <= 0 else min(max_pages, len(doc))
        for page_index in range(total_pages):
            page_number = page_index + 1
            page_path = page_dir / f"page_{page_number:03d}.json"
            if page_path.exists() and not force:
                raw_blocks = json.loads(page_path.read_text(encoding="utf-8"))
            else:
                page = doc[page_index]
                pix = page.get_pixmap(matrix=fitz.Matrix(adapter.render_scale, adapter.render_scale), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                raw_result = adapter.client.two_step_extract(image)
                raw_blocks = [dict(block) for block in raw_result]
                page_path.write_text(json.dumps(raw_blocks, indent=2, ensure_ascii=False), encoding="utf-8")
            raw_pages.append({"page": page_number, "blocks": raw_blocks})
            blocks.extend(adapter.normalize_page_result(raw_blocks, page=page_number, block_offset=len(blocks)))

    raw_payload = {
        "pages": raw_pages,
        "stats": {
            "parser": adapter.NAME,
            "model": adapter.model_path,
            "backend": adapter.backend,
            "pages": len(raw_pages),
            "total_blocks": len(blocks),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "load_seconds": round(adapter.load_seconds, 3),
            "max_pages": max_pages,
        },
    }
    return blocks, raw_payload


def pdf_stats(pdf_path: Path) -> tuple[int, int]:
    doc = fitz.open(str(pdf_path))
    try:
        formula_like_lines = 0
        for page in doc:
            lines = [line.strip() for line in page.get_text("text").splitlines() if line.strip()]
            formula_like_lines += sum(1 for line in lines if len(line) < 180 and FORMULA_LINE_RE.search(line))
        return len(doc), formula_like_lines
    finally:
        doc.close()


def canonical_match_count(formulas: Iterable[Any], canonical_text: str) -> int:
    normalized = normalize_match(canonical_text)
    count = 0
    for formula in formulas:
        latex = getattr(formula, "latex", "")
        raw = getattr(formula, "raw_formula_text", "")
        needle = normalize_match(latex or raw)
        if needle and needle in normalized:
            count += 1
    return count


def acceptance_reasons(metrics: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if metrics["max_pages"]:
        reasons.append("SMOKE_MAX_PAGES_NOT_FORMAL_ACCEPTANCE")
    if metrics["primary_parser"] != "mineru25pro":
        reasons.append("PRIMARY_PARSER_NOT_MINERU25PRO")
    if metrics["fallback_used"]:
        reasons.append("FALLBACK_USED")
    if metrics["quality_status"] != "PASS":
        reasons.append("QUALITY_STATUS_NOT_PASS")
    if not metrics["title_ok"]:
        reasons.append("TITLE_NOT_CONFIRMED")
    formula_count = int(metrics["formula_count"])
    if formula_count < 5:
        reasons.append("FORMULA_COUNT_LT_5")
    if int(metrics["body_formula_count"]) < 5:
        reasons.append("BODY_FORMULA_COUNT_LT_5")
    if int(metrics["latex_count"]) <= 0:
        reasons.append("LATEX_COUNT_ZERO")
    for key in ("bbox_count", "crop_count", "overlay_count", "canonical_match_count"):
        if int(metrics[key]) != formula_count:
            reasons.append(f"{key.upper()}_NE_FORMULA_COUNT")
    if metrics["polluted_section_count"]:
        reasons.append("POLLUTED_SECTION_COUNT_NONZERO")
    if metrics["section_contradiction_count"]:
        reasons.append("SECTION_CONTRADICTION_NONZERO")
    if metrics["all_Abstract"]:
        reasons.append("ALL_ABSTRACT_TRUE")
    if metrics["high_risk_count"]:
        reasons.append("HIGH_RISK_NONZERO")
    if not metrics["m2_ready"]:
        reasons.append("M2_READY_FALSE")
    if not metrics["formula_m2_ready"]:
        reasons.append("FORMULA_M2_READY_FALSE")
    return reasons


def normalize_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def candidate_to_json(candidate: Candidate) -> dict[str, Any]:
    data = candidate.__dict__.copy()
    data["local_pdf"] = f"_candidate_downloads/{candidate.local_pdf.name}"
    return data


def render_paper_readme(candidate: Candidate, metrics: dict[str, Any]) -> str:
    return "\n".join([
        f"# {candidate.key} MinerU Primary Acceptance",
        "",
        f"- title: {candidate.title}",
        f"- pdf_url: {candidate.pdf_url}",
        f"- primary_parser: {metrics['primary_parser']}",
        f"- fallback_used: {metrics['fallback_used']}",
        f"- title_ok: {metrics['title_ok']}",
        f"- status: {metrics['status']}",
        f"- quality_status: {metrics['quality_status']}",
        f"- m2_ready: {metrics['m2_ready']}",
        f"- formula_m2_ready: {metrics['formula_m2_ready']}",
        f"- formula_count: {metrics['formula_count']}",
        f"- body_formula_count: {metrics['body_formula_count']}",
        f"- reference_formula_count: {metrics['reference_formula_count']}",
        f"- latex_count: {metrics['latex_count']}",
        f"- bbox_count: {metrics['bbox_count']}",
        f"- crop_count: {metrics['crop_count']}",
        f"- overlay_count: {metrics['overlay_count']}",
        f"- canonical_match_count: {metrics['canonical_match_count']}",
        f"- high_risk_count: {metrics['high_risk_count']}",
        f"- blocking_reasons: {metrics['blocking_reasons']}",
        f"- warning_reasons: {metrics['warning_reasons']}",
        f"- acceptance_reasons: {metrics['acceptance_reasons']}",
        f"- runtime_seconds: {metrics['runtime_seconds']}",
        f"- max_pages: {metrics['max_pages']}",
        "",
    ])


def write_top_level(candidates: list[Candidate], rows: list[dict[str, Any]], *, max_pages: int) -> None:
    lines = [
        "# M1 v2 MinerU Primary Acceptance",
        "",
        "Primary route: MinerU2.5-Pro via mineru-vl-utils + RuleBasedStructureRefiner.",
        "Fallback parsers are not used for PASS claims in this report.",
        f"Acceptance mode: {'SMOKE (max_pages set)' if max_pages else 'FULL PAPER'}",
        "",
        "## Candidate Search",
        "",
        "| key | title | pages | formula_like_lines | query |",
        "| --- | ----- | ----: | -----------------: | ----- |",
    ]
    for candidate in candidates:
        lines.append(
            f"| {candidate.key} | {candidate.title} | {candidate.pages} | "
            f"{candidate.formula_like_lines} | {candidate.query} |"
        )
    lines += [
        "",
        "## Results",
        "",
        "| key | status | parser | fallback | title_ok | quality | m2_ready | formula_m2_ready | formulas | body | refs | latex | bbox | crops | overlays | canonical_match | high_risk |",
        "| --- | ------ | ------ | -------- | -------- | ------- | -------- | ---------------- | -------: | ---: | ---: | ----: | ---: | ----: | -------: | --------------: | --------: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['paper_key']} | {row['status']} | {row['primary_parser']} | {row['fallback_used']} | {row['title_ok']} | "
            f"{row['quality_status']} | {row['m2_ready']} | {row['formula_m2_ready']} | "
            f"{row['formula_count']} | {row['body_formula_count']} | {row['reference_formula_count']} | "
            f"{row['latex_count']} | {row['bbox_count']} | {row['crop_count']} | "
            f"{row['overlay_count']} | {row['canonical_match_count']} | {row['high_risk_count']} |"
        )
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def make_bundle() -> Path:
    bundle = OUT.with_name("m1_v2_mineru_primary_acceptance_bundle.zip")
    if bundle.exists():
        bundle.unlink()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in OUT.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and "_candidate_downloads" not in path.parts:
                zf.write(path, path.relative_to(OUT.parent))
    return bundle


if __name__ == "__main__":
    raise SystemExit(main())
