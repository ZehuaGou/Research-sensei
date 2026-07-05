"""M1 Unseen Paper Search — 3-stage pipeline for discovering new acceptance papers.

Stage A: metadata-only search (no PDF downloads)
Stage B: limited PDF prescreen (top N candidates only)
Stage C: selected paper output (1 paper for full MinerU parse)

Default limits:
  --max-pdf-downloads 3   (Stage B)
  --full-parse-limit 1    (Stage C, used by acceptance runner)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import arxiv
import fitz
import httpx

ROOT = Path(__file__).resolve().parents[1]

# --- Exclusion list: papers already used in M1 acceptance ---
EXCLUDED_IDS = {
    "2310.08800",  # DDMT
    "2508.11528",  # TPIDM
    "2312.02530",  # MEMTO
    "2106.02775",  # TranAD
    "2209.07142",  # Monte Carlo EM (paper_1)
    "2012.09149",  # GTA (paper_2)
    "2407.06849",  # TeVAE (already accepted)
}
EXCLUDED_TITLE_RE = re.compile(
    r"monte carlo em|learning graph structures with transformer|anomaly transformer|memto|tranad|tevae",
    re.I,
)
REJECT_TITLE_RE = re.compile(
    r"survey|review|forecast\b|forecasting|classification|taxonomy|benchmarking|benchmark\b",
    re.I,
)
THEME_RE = re.compile(
    r"transformer|diffusion|graph.*(neural|attention)|attention.*(mechanism|network)|"
    r"autoencoder|vae|variational|generative|contrastive|self-supervised|"
    r"imputation|interpolation|missing.*(data|value)",
    re.I,
)
FORMULA_LINE_RE = re.compile(
    r"(=|\\frac|\\sum|\\prod|\\arg|softmax|attention|\bL\s*=|\bx_\{|\bx_t|\bz_t|"
    r"\bscore\b|\banomaly\s*score\b|\bloss\b|\bmin\b|\bmax\b|\b\\mathbb\b|\b\\mathrm\b)",
    re.I,
)

QUERIES = [
    "time series anomaly detection transformer",
    "multivariate time series anomaly detection deep learning",
    "time series anomaly detection diffusion model",
    "time series imputation transformer",
    "time series imputation deep learning missing data",
    "transformer time series long-term dependency",
    "graph neural network time series anomaly",
    "contrastive learning time series anomaly detection",
    "variational autoencoder time series anomaly",
    "self-supervised time series anomaly detection",
]


# ──────────────────────────── helpers ────────────────────────────

def compute_topic_score(title: str, abstract: str) -> float:
    text = f"{title} {abstract}".lower()
    score = 0.0
    keywords = {
        "anomaly": 0.15, "detection": 0.10, "time series": 0.15,
        "multivariate": 0.05, "transformer": 0.10, "attention": 0.05,
        "diffusion": 0.08, "graph": 0.05, "neural": 0.03,
        "deep learning": 0.05, "imputation": 0.08, "missing": 0.03,
        "autoencoder": 0.05, "vae": 0.03, "contrastive": 0.05,
        "self-supervised": 0.04, "generative": 0.03,
    }
    for kw, weight in keywords.items():
        if kw in text:
            score += weight
    if "anomaly" in title.lower() and "time" in title.lower():
        score += 0.1
    return min(score, 1.0)


def prescreen_formula_count(pdf_path: Path) -> int:
    """Count formula-like lines via PyMuPDF text scan. NOT MinerU final count."""
    try:
        doc = fitz.open(str(pdf_path))
        count = 0
        for page in doc:
            text = page.get_text()
            for line in text.splitlines():
                if FORMULA_LINE_RE.search(line):
                    count += 1
        doc.close()
        return count
    except Exception:
        return 0


def download_pdf(url: str, dest: Path, http: httpx.Client) -> bool:
    try:
        resp = http.get(url)
        if resp.status_code != 200:
            return False
        if b"%PDF" not in resp.content[:20]:
            return False
        if len(resp.content) < 10000:
            return False
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def write_rejected(candidates: list[dict], path: Path) -> None:
    lines = ["# Rejected Candidates", "", f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}", ""]
    rejected = [c for c in candidates if c["exclusion_status"] == "excluded"]
    lines.append(f"Total rejected: {len(rejected)}")
    lines.append("")
    lines.append("| arXiv ID | Title | Reason |")
    lines.append("|----------|-------|--------|")
    for c in rejected:
        title_short = c["title"][:60] + ("..." if len(c["title"]) > 60 else "")
        lines.append(f"| {c['arxiv_id']} | {title_short} | {c['exclusion_reason']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


# ──────────────────────────── Stage A ────────────────────────────

def stage_a_metadata_search(
    *,
    queries: list[str],
    max_results_per_query: int,
    excluded_ids: set[str],
) -> tuple[list[dict], dict]:
    """Search arXiv metadata only. No PDF downloads."""
    print("\n[Stage A] Metadata search...")
    start = time.time()
    client = arxiv.Client(page_size=20, delay_seconds=1.0, num_retries=3)
    seen_ids: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        print(f"  query: {query}")
        search = arxiv.Search(query=query, max_results=max_results_per_query, sort_by=arxiv.SortCriterion.Relevance)
        try:
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/abs/")[-1]
                base_id = re.sub(r"v\d+$", "", arxiv_id)
                if base_id in seen_ids:
                    continue
                seen_ids.add(base_id)

                title = " ".join(result.title.split())
                abstract = result.summary.strip()
                text = f"{title} {abstract}"
                published = result.published.strftime("%Y-%m-%d") if result.published else ""
                pdf_url = result.pdf_url or ""

                exclusion_reason = ""
                if base_id in excluded_ids:
                    exclusion_reason = "already_used"
                elif EXCLUDED_TITLE_RE.search(title):
                    exclusion_reason = "already_used_title_match"
                elif REJECT_TITLE_RE.search(title):
                    exclusion_reason = "survey_or_review"
                elif not THEME_RE.search(text):
                    exclusion_reason = "unrelated_topic"
                elif not pdf_url:
                    exclusion_reason = "no_public_pdf"

                topic_score = compute_topic_score(title, abstract)

                candidates.append({
                    "arxiv_id": base_id,
                    "title": title,
                    "abstract": abstract[:500],
                    "pdf_url": pdf_url,
                    "published": published,
                    "authors": [a.name for a in (result.authors or [])[:5]],
                    "query": query,
                    "topic_score": topic_score,
                    "formula_prescreen_count": 0,
                    "formula_prescreen_note": "PyMuPDF text-line heuristic, NOT MinerU final count",
                    "pdf_downloaded": False,
                    "prescreen_elapsed_seconds": 0.0,
                    "download_elapsed_seconds": 0.0,
                    "exclusion_status": "excluded" if exclusion_reason else "candidate",
                    "exclusion_reason": exclusion_reason,
                    "selected_candidate": False,
                })
        except Exception as e:
            print(f"  WARNING: query '{query}' failed: {e}")

    elapsed = time.time() - start
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    stats = {
        "stage": "A",
        "description": "Metadata-only search, no PDF downloads",
        "raw_candidate_count": len(candidates),
        "valid_candidate_count": len(valid),
        "excluded_count": len(candidates) - len(valid),
        "elapsed_seconds": round(elapsed, 1),
        "pdf_downloaded_count": 0,
    }
    print(f"  Raw: {len(candidates)}, Valid: {len(valid)}, Excluded: {stats['excluded_count']}")
    return candidates, stats


# ──────────────────────────── Stage B ────────────────────────────

def stage_b_limited_prescreen(
    candidates: list[dict],
    *,
    download_dir: Path,
    max_pdf_downloads: int,
    min_formula_prescreen: int,
    reuse_cache: bool,
    force_redownload: bool,
) -> dict:
    """Download PDFs for top-N candidates and prescreen formulas."""
    print(f"\n[Stage B] Limited PDF prescreen (max {max_pdf_downloads} downloads)...")
    start = time.time()
    download_dir.mkdir(parents=True, exist_ok=True)

    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    valid.sort(key=lambda c: c["topic_score"], reverse=True)
    top_n = valid[:max_pdf_downloads]

    print(f"  Top {len(top_n)} candidates by topic_score:")
    for i, c in enumerate(top_n, 1):
        print(f"    {i}. {c['arxiv_id']} score={c['topic_score']:.2f}")

    http = httpx.Client(timeout=60, follow_redirects=True)
    downloaded_count = 0

    for c in top_n:
        arxiv_id = c["arxiv_id"]
        pdf_path = download_dir / f"{arxiv_id.replace('.', '_')}.pdf"

        dl_start = time.time()
        if pdf_path.exists() and reuse_cache and not force_redownload:
            print(f"  [cached] {arxiv_id}")
            c["download_elapsed_seconds"] = 0.0
        else:
            print(f"  [download] {arxiv_id}...", end=" ", flush=True)
            ok = download_pdf(c["pdf_url"], pdf_path, http)
            c["download_elapsed_seconds"] = round(time.time() - dl_start, 1)
            if not ok:
                c["exclusion_status"] = "excluded"
                c["exclusion_reason"] = "pdf_download_failed"
                print("FAIL")
                continue
            downloaded_count += 1
            print(f"OK ({c['download_elapsed_seconds']}s)")

        c["pdf_downloaded"] = True
        prescreen_start = time.time()
        c["formula_prescreen_count"] = prescreen_formula_count(pdf_path)
        c["prescreen_elapsed_seconds"] = round(time.time() - prescreen_start, 1)
        print(f"    prescreen_formula_lines={c['formula_prescreen_count']} ({c['prescreen_elapsed_seconds']}s)")

    http.close()

    # Mark candidates beyond max_pdf_downloads as not downloaded
    for c in candidates:
        if c not in top_n:
            c["pdf_downloaded"] = False

    # Filter by min formula prescreen
    for c in top_n:
        if c["exclusion_status"] == "candidate" and c["formula_prescreen_count"] < min_formula_prescreen:
            c["exclusion_status"] = "excluded"
            c["exclusion_reason"] = f"formula_prescreen_below_{min_formula_prescreen}"

    elapsed = time.time() - start
    still_valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    stats = {
        "stage": "B",
        "description": f"Limited PDF prescreen, max {max_pdf_downloads} downloads",
        "pdf_downloaded_count": downloaded_count,
        "cached_count": len([c for c in top_n if c["pdf_downloaded"] and c["download_elapsed_seconds"] == 0.0]),
        "prescreened_count": len([c for c in top_n if c["formula_prescreen_count"] > 0]),
        "valid_after_prescreen": len(still_valid),
        "elapsed_seconds": round(elapsed, 1),
    }
    print(f"  Downloaded: {downloaded_count}, Valid after prescreen: {len(still_valid)}")
    return stats


# ──────────────────────────── Stage C ────────────────────────────

def stage_c_select_paper(candidates: list[dict]) -> dict | None:
    """Select the best candidate."""
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    if not valid:
        return None
    max_formula = max((c["formula_prescreen_count"] for c in valid), default=1) or 1
    for c in valid:
        formula_norm = c["formula_prescreen_count"] / max_formula
        c["_combined_score"] = c["topic_score"] * 0.6 + formula_norm * 0.4
    valid.sort(key=lambda c: c["_combined_score"], reverse=True)
    return valid[0]


# ──────────────────────────── main ────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="M1 Unseen Paper Search (3-stage)")
    p.add_argument("--max-results-per-query", type=int, default=10)
    p.add_argument("--max-metadata-candidates", type=int, default=30)
    p.add_argument("--max-pdf-downloads", type=int, default=3)
    p.add_argument("--min-formula-prescreen-count", type=int, default=5)
    p.add_argument("--reuse-cache", action="store_true", default=True)
    p.add_argument("--force-redownload", action="store_true", default=False)
    p.add_argument("--dry-run", action="store_true", default=False)
    p.add_argument("--full-parse-limit", type=int, default=1)
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument("--queries", type=str, nargs="*", default=None)
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    out = Path(args.output_dir) if args.output_dir else ROOT / "reports" / "m1_unseen_paper_search"
    out.mkdir(parents=True, exist_ok=True)
    download_dir = out / "_downloads"

    queries = args.queries or QUERIES

    if args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        print("=" * 60)
        print("M1 Unseen Paper Search (dry-run)")
        print(f"  max_results_per_query={args.max_results_per_query}")
        print(f"  max_pdf_downloads={args.max_pdf_downloads}")
        print(f"  full_parse_limit={args.full_parse_limit}")
        print("  external_search=skipped")
        print("=" * 60)
        stats_a = {
            "stage": "A",
            "description": "Dry-run configuration check; external metadata search skipped",
            "raw_candidate_count": 0,
            "valid_candidate_count": 0,
            "excluded_count": 0,
            "elapsed_seconds": 0.0,
            "pdf_downloaded_count": 0,
        }
        _write_outputs(out, [], None, stats_a, {}, args)
        return 0

    print("=" * 60)
    print("M1 Unseen Paper Search (3-stage)")
    print(f"  max_results_per_query={args.max_results_per_query}")
    print(f"  max_pdf_downloads={args.max_pdf_downloads}")
    print(f"  min_formula_prescreen={args.min_formula_prescreen_count}")
    print(f"  full_parse_limit={args.full_parse_limit}")
    print(f"  dry_run={args.dry_run}")
    print("=" * 60)

    # ── Stage A ──
    candidates, stats_a = stage_a_metadata_search(
        queries=queries,
        max_results_per_query=args.max_results_per_query,
        excluded_ids=EXCLUDED_IDS,
    )

    # Trim to max_metadata_candidates
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    if len(valid) > args.max_metadata_candidates:
        valid.sort(key=lambda c: c["topic_score"], reverse=True)
        keep_ids = {c["arxiv_id"] for c in valid[: args.max_metadata_candidates]}
        for c in candidates:
            if c["exclusion_status"] == "candidate" and c["arxiv_id"] not in keep_ids:
                c["exclusion_status"] = "excluded"
                c["exclusion_reason"] = "below_max_metadata_candidates"
        print(f"  Trimmed to top {args.max_metadata_candidates} metadata candidates")

    if args.dry_run:
        print("\n[dry-run] Stopping after Stage A. No PDFs downloaded.")
        _write_outputs(out, candidates, None, stats_a, {}, args)
        return 0

    # ── Stage B ──
    stats_b = stage_b_limited_prescreen(
        candidates,
        download_dir=download_dir,
        max_pdf_downloads=args.max_pdf_downloads,
        min_formula_prescreen=args.min_formula_prescreen_count,
        reuse_cache=args.reuse_cache,
        force_redownload=args.force_redownload,
    )

    # ── Stage C ──
    print("\n[Stage C] Selecting best candidate...")
    best = stage_c_select_paper(candidates)

    if best is None:
        print("  ERROR: No valid candidate found!")
        _write_outputs(out, candidates, None, stats_a, stats_b, args)
        return 1

    best["selected_candidate"] = True
    print(f"  Selected: {best['arxiv_id']} - {best['title']}")
    print(f"  topic_score={best['topic_score']:.2f}, prescreen_formula_lines={best['formula_prescreen_count']}")

    # Write all outputs
    _write_outputs(out, candidates, best, stats_a, stats_b, args)

    # Summary
    print("\n" + "=" * 60)
    print("SEARCH COST SUMMARY")
    print(f"  Stage A (metadata): {stats_a['raw_candidate_count']} candidates, 0 PDF downloads")
    print(f"  Stage B (prescreen): {stats_b['pdf_downloaded_count']} PDFs downloaded, {stats_b['prescreened_count']} prescreened")
    print(f"  Stage C (selected): 1 paper selected for full MinerU parse")
    print(f"  formula_prescreen_count = PyMuPDF text-line heuristic (NOT MinerU final)")
    print(f"  formula_slots will come from the acceptance runner (MinerU full parse)")
    print("=" * 60)
    return 0


def _write_outputs(
    out: Path,
    candidates: list[dict],
    best: dict | None,
    stats_a: dict,
    stats_b: dict,
    args: argparse.Namespace,
) -> None:
    # search_config.json
    config = {
        "search_date": datetime.datetime.now().isoformat(),
        "cli_args": {
            "max_results_per_query": args.max_results_per_query,
            "max_metadata_candidates": args.max_metadata_candidates,
            "max_pdf_downloads": args.max_pdf_downloads,
            "min_formula_prescreen_count": args.min_formula_prescreen_count,
            "full_parse_limit": args.full_parse_limit,
            "reuse_cache": args.reuse_cache,
            "force_redownload": args.force_redownload,
            "dry_run": args.dry_run,
        },
        "queries": args.queries or QUERIES,
        "excluded_ids": sorted(EXCLUDED_IDS),
        "stage_a_stats": stats_a,
        "stage_b_stats": stats_b,
        "search_cost_summary": {
            "total_candidates": stats_a.get("raw_candidate_count", 0),
            "valid_after_metadata": stats_a.get("valid_candidate_count", 0),
            "pdfs_downloaded": stats_b.get("pdf_downloaded_count", 0),
            "prescreened": stats_b.get("prescreened_count", 0),
            "selected_for_full_parse": 1 if best else 0,
            "note": "formula_prescreen_count is PyMuPDF text-line heuristic, NOT MinerU final formula count",
        },
    }
    (out / "search_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # metadata_candidates.json (Stage A output)
    for c in candidates:
        c.pop("_combined_score", None)
    (out / "metadata_candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # rejected_candidates.md
    write_rejected(candidates, out / "rejected_candidates.md")

    if best is None:
        (out / "paper_search_report.md").write_text(
            f"# M1 Paper Search Report\n\n**Result**: FAILED\n\nNo valid candidate found.\n",
            encoding="utf-8",
        )
        return

    # PDF hash
    pdf_path = out / "_downloads" / f"{best['arxiv_id'].replace('.', '_')}.pdf"
    pdf_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest() if pdf_path.exists() else ""

    # selected_paper_metadata.json
    selected_meta = {
        "paper_id": best["arxiv_id"].replace(".", "_"),
        "title": best["title"],
        "arxiv_id": best["arxiv_id"],
        "pdf_url": best["pdf_url"],
        "abstract": best["abstract"],
        "authors": best["authors"],
        "published": best["published"],
        "selected_reason": (
            f"Highest combined score (topic={best['topic_score']:.2f}, "
            f"prescreen_formula_lines={best['formula_prescreen_count']}). "
            f"Query: '{best['query']}'. Not previously used in M1 acceptance."
        ),
        "search_query_that_found_it": best["query"],
        "formula_prescreen_count": best["formula_prescreen_count"],
        "formula_prescreen_note": "PyMuPDF text-line heuristic, NOT MinerU final count",
        "downloaded_pdf_sha256": pdf_sha256,
        "downloaded_pdf_path": str(pdf_path),
        "timestamp": datetime.datetime.now().isoformat(),
    }
    (out / "selected_paper_metadata.json").write_text(
        json.dumps(selected_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # paper_search_report.md
    valid_count = len([c for c in candidates if c["exclusion_status"] == "candidate"])
    excluded_count = len(candidates) - valid_count
    report_lines = [
        "# M1 Unseen Paper Search Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Search Cost Summary",
        "",
        f"| Stage | Description | Count |",
        f"|-------|-------------|------:|",
        f"| A | Metadata candidates (no download) | {stats_a.get('raw_candidate_count', 0)} |",
        f"| A | Valid after metadata filter | {stats_a.get('valid_candidate_count', 0)} |",
        f"| B | PDFs downloaded (max {args.max_pdf_downloads}) | {stats_b.get('pdf_downloaded_count', 0)} |",
        f"| B | Prescreened (formula_lines via PyMuPDF) | {stats_b.get('prescreened_count', 0)} |",
        f"| C | Selected for full MinerU parse | 1 |",
        "",
        "**Note**: `formula_prescreen_count` is a PyMuPDF text-line heuristic. It is NOT the MinerU final formula count. "
        "The actual `formula_slots` count comes from the acceptance runner's full MinerU parse.",
        "",
        "## Selected Paper",
        "",
        f"- **arXiv**: {best['arxiv_id']}",
        f"- **Title**: {best['title']}",
        f"- **topic_score**: {best['topic_score']:.2f}",
        f"- **prescreen_formula_lines**: {best['formula_prescreen_count']}",
        f"- **query**: `{best['query']}`",
        "",
        "## Exclusion Summary",
        "",
    ]
    reason_counts: dict[str, int] = {}
    for c in candidates:
        r = c.get("exclusion_reason", "")
        if r:
            reason_counts[r] = reason_counts.get(r, 0) + 1
    for reason, count in sorted(reason_counts.items()):
        report_lines.append(f"- {reason}: {count}")

    report_lines += [
        "",
        "## Top Candidates (by topic_score)",
        "",
        "| # | arXiv ID | Title | Score | Prescreen | Downloaded | Status |",
        "|---|----------|-------|------:|----------:|:----------:|--------|",
    ]
    sorted_cands = sorted(candidates, key=lambda c: c["topic_score"], reverse=True)[:10]
    for i, c in enumerate(sorted_cands, 1):
        title_short = c["title"][:50] + ("..." if len(c["title"]) > 50 else "")
        status = "SELECTED" if c["selected_candidate"] else c["exclusion_status"]
        dl = "Y" if c.get("pdf_downloaded") else "N"
        report_lines.append(
            f"| {i} | {c['arxiv_id']} | {title_short} | {c['topic_score']:.2f} "
            f"| {c['formula_prescreen_count']} | {dl} | {status} |"
        )
    (out / "paper_search_report.md").write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
