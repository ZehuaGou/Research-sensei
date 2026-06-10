"""M1 Unseen Paper Search — discover a new paper for M1 acceptance testing.

Searches arXiv for time-series / anomaly-detection papers, filters out
previously-used papers, scores candidates, selects the best one, and
downloads its PDF.  All artifacts are written to reports/m1_unseen_paper_search/.
"""
from __future__ import annotations

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
OUT = ROOT / "reports" / "m1_unseen_paper_search"

# --- Exclusion list: papers already used in M1 acceptance ---
EXCLUDED_IDS = {
    "2310.08800",  # DDMT
    "2508.11528",  # TPIDM
    "2312.02530",  # MEMTO
    "2106.02775",  # TranAD
    "2209.07142",  # Monte Carlo EM (paper_1)
    "2012.09149",  # GTA (paper_2)
    "2205.05tried",  # placeholder
}
EXCLUDED_TITLE_RE = re.compile(
    r"monte carlo em|learning graph structures with transformer|anomaly transformer|memto|tranad",
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

# --- Search queries ---
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


def search_candidates(download_dir: Path) -> list[dict]:
    """Search arXiv and return raw candidate dicts."""
    download_dir.mkdir(parents=True, exist_ok=True)
    client = arxiv.Client(page_size=20, delay_seconds=1.0, num_retries=3)
    http = httpx.Client(timeout=60, follow_redirects=True)
    seen_ids: set[str] = set()
    candidates: list[dict] = []

    for query in QUERIES:
        print(f"[search] query: {query}")
        search = arxiv.Search(
            query=query, max_results=20, sort_by=arxiv.SortCriterion.Relevance
        )
        try:
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/abs/")[-1]
                # Strip version suffix for dedup
                base_id = re.sub(r"v\d+$", "", arxiv_id)
                if base_id in seen_ids:
                    continue
                seen_ids.add(base_id)

                title = " ".join(result.title.split())
                abstract = result.summary.strip()
                text = f"{title} {abstract}"
                published = result.published.strftime("%Y-%m-%d") if result.published else ""
                pdf_url = result.pdf_url or ""

                # Exclusion checks
                exclusion_reason = ""
                if base_id in EXCLUDED_IDS:
                    exclusion_reason = "already_used"
                elif EXCLUDED_TITLE_RE.search(title):
                    exclusion_reason = "already_used_title_match"
                elif REJECT_TITLE_RE.search(title):
                    exclusion_reason = "survey_or_review"
                elif not THEME_RE.search(text):
                    exclusion_reason = "unrelated_topic"
                elif not pdf_url:
                    exclusion_reason = "no_public_pdf"

                # Topic score
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
                    "exclusion_status": "excluded" if exclusion_reason else "candidate",
                    "exclusion_reason": exclusion_reason,
                    "selected_candidate": False,
                })
        except Exception as e:
            print(f"[search] WARNING: query '{query}' failed: {e}")
            continue

    http.close()
    return candidates


def compute_topic_score(title: str, abstract: str) -> float:
    """Score topic relevance 0-1."""
    text = f"{title} {abstract}".lower()
    score = 0.0
    # Core topic keywords
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
    # Title bonus
    if "anomaly" in title.lower() and "time" in title.lower():
        score += 0.1
    return min(score, 1.0)


def prescreen_formula_count(pdf_path: Path) -> int:
    """Count formula-like lines in a PDF using PyMuPDF."""
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
    """Download a PDF and validate it."""
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


def select_best(candidates: list[dict]) -> dict | None:
    """Select the best candidate based on topic_score and formula count."""
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    if not valid:
        return None
    # Sort by combined score: topic_score * 0.6 + formula_norm * 0.4
    max_formula = max((c["formula_prescreen_count"] for c in valid), default=1) or 1
    for c in valid:
        formula_norm = c["formula_prescreen_count"] / max_formula
        c["_combined_score"] = c["topic_score"] * 0.6 + formula_norm * 0.4
    valid.sort(key=lambda c: c["_combined_score"], reverse=True)
    return valid[0]


def write_rejected(candidates: list[dict], path: Path) -> None:
    """Write rejected_candidates.md."""
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


def main() -> int:
    print("=" * 60)
    print("M1 Unseen Paper Search")
    print("=" * 60)

    OUT.mkdir(parents=True, exist_ok=True)
    download_dir = OUT / "_downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Search
    print("\n[1/5] Searching arXiv...")
    candidates = search_candidates(download_dir)
    print(f"  Found {len(candidates)} raw candidates")

    # Step 2: Filter and pre-screen
    print("\n[2/5] Filtering and pre-screening...")
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    print(f"  {len(valid)} candidates pass initial filter")
    excluded = [c for c in candidates if c["exclusion_status"] == "excluded"]
    print(f"  {len(excluded)} excluded")

    # Download PDFs and count formulas for valid candidates
    http = httpx.Client(timeout=60, follow_redirects=True)
    for c in valid:
        arxiv_id = c["arxiv_id"]
        pdf_path = download_dir / f"{arxiv_id.replace('.', '_')}.pdf"
        if pdf_path.exists():
            print(f"  [cached] {arxiv_id}")
        else:
            print(f"  [download] {arxiv_id}...", end=" ", flush=True)
            ok = download_pdf(c["pdf_url"], pdf_path, http)
            if not ok:
                c["exclusion_status"] = "excluded"
                c["exclusion_reason"] = "pdf_download_failed"
                print("FAIL")
                continue
            print("OK")
        c["formula_prescreen_count"] = prescreen_formula_count(pdf_path)
        print(f"    formula_lines={c['formula_prescreen_count']}")
    http.close()

    # Re-filter after download
    valid = [c for c in candidates if c["exclusion_status" ] == "candidate"]
    low_formula = [c for c in valid if c["formula_prescreen_count"] < 5]
    for c in low_formula:
        c["exclusion_status"] = "excluded"
        c["exclusion_reason"] = "formula_count_below_5"
    valid = [c for c in candidates if c["exclusion_status"] == "candidate"]
    print(f"  {len(valid)} candidates with formula_count >= 5")

    # Step 3: Select best
    print("\n[3/5] Selecting best candidate...")
    best = select_best(candidates)
    if best is None:
        print("  ERROR: No valid candidate found!")
        # Write failure report
        (OUT / "paper_search_report.md").write_text(
            f"# M1 Paper Search Report\n\n**Result**: FAILED\n\nNo valid candidate found.\n"
            f"Total candidates: {len(candidates)}\nExcluded: {len(excluded)}\n",
            encoding="utf-8",
        )
        write_rejected(candidates, OUT / "rejected_candidates.md")
        (OUT / "candidate_papers.json").write_text(
            json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return 1

    best["selected_candidate"] = True
    print(f"  Selected: {best['arxiv_id']} - {best['title']}")
    print(f"  topic_score={best['topic_score']:.2f}, formula_lines={best['formula_prescreen_count']}")

    # Step 4: Write artifacts
    print("\n[4/5] Writing artifacts...")

    # search_config.json
    config = {
        "search_date": datetime.datetime.now().isoformat(),
        "queries": QUERIES,
        "excluded_ids": sorted(EXCLUDED_IDS),
        "filters": {
            "reject_title_pattern": REJECT_TITLE_RE.pattern,
            "theme_pattern": THEME_RE.pattern,
            "min_formula_count": 5,
        },
        "scoring": {
            "topic_score_weight": 0.6,
            "formula_count_weight": 0.4,
            "topic_keywords": list(FORMULA_LINE_RE.pattern.split("|")),
        },
    }
    (OUT / "search_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # search_queries.json
    (OUT / "search_queries.json").write_text(
        json.dumps({"queries": QUERIES, "total_candidates": len(candidates)}, indent=2),
        encoding="utf-8",
    )

    # candidate_papers.json
    for c in candidates:
        c.pop("_combined_score", None)
    (OUT / "candidate_papers.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # rejected_candidates.md
    write_rejected(candidates, OUT / "rejected_candidates.md")

    # Compute PDF hash
    pdf_path = download_dir / f"{best['arxiv_id'].replace('.', '_')}.pdf"
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
            f"formula_lines={best['formula_prescreen_count']}). "
            f"Query: '{best['query']}'. "
            f"Not previously used in M1 acceptance."
        ),
        "search_query_that_found_it": best["query"],
        "formula_prescreen_count": best["formula_prescreen_count"],
        "downloaded_pdf_sha256": pdf_sha256,
        "downloaded_pdf_path": str(pdf_path),
        "timestamp": datetime.datetime.now().isoformat(),
    }
    (OUT / "selected_paper_metadata.json").write_text(
        json.dumps(selected_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # paper_search_report.md
    report_lines = [
        "# M1 Unseen Paper Search Report",
        "",
        f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Search Summary",
        "",
        f"- Total candidates found: {len(candidates)}",
        f"- Excluded: {len([c for c in candidates if c['exclusion_status'] == 'excluded'])}",
        f"- Valid (formula >= 5): {len([c for c in candidates if c['exclusion_status'] == 'candidate'])}",
        f"- Selected: **{best['arxiv_id']}** — {best['title']}",
        "",
        "## Scoring",
        "",
        f"- topic_score: {best['topic_score']:.2f}",
        f"- formula_prescreen_count: {best['formula_prescreen_count']}",
        f"- query: `{best['query']}`",
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
        "## Candidate List (top 10 by topic_score)",
        "",
        "| # | arXiv ID | Title | Topic | Formulas | Status |",
        "|---|----------|-------|------:|--------:|--------|",
    ]
    sorted_cands = sorted(candidates, key=lambda c: c["topic_score"], reverse=True)[:10]
    for i, c in enumerate(sorted_cands, 1):
        title_short = c["title"][:50] + ("..." if len(c["title"]) > 50 else "")
        status = "SELECTED" if c["selected_candidate"] else c["exclusion_status"]
        report_lines.append(
            f"| {i} | {c['arxiv_id']} | {title_short} | {c['topic_score']:.2f} "
            f"| {c['formula_prescreen_count']} | {status} |"
        )
    (OUT / "paper_search_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"  Artifacts written to {OUT}")

    # Step 5: Summary
    print("\n[5/5] Search complete.")
    print(f"  Selected paper: {best['arxiv_id']} - {best['title']}")
    print(f"  PDF: {pdf_path}")
    print(f"  SHA256: {pdf_sha256[:16]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
