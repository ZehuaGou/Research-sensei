"""M1 target-mode generalization checks.

Default behavior is intentionally lightweight: metadata search plus static
contract checks over existing M1 artifacts. It does not run full MinerU unless
future callers explicitly add a live evaluator.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.m2.artifact_reader import validate_m1_contract, parse_front_matter  # noqa: E402


KNOWN_EXCLUDED_IDS = {
    "2510.18998",
    "2510_18998",
    "2310.08800",
    "2310_08800v2",
    "2508.11528",
    "2508_11528v1",
    "2312.02530",
    "2407.06849",
    "2209.07142",
    "2012.09149",
    "2106.02775",
}

KNOWN_EXCLUDED_TITLE_RE = re.compile(
    r"ddmt|tpidm|memto|tevae|tranad|encode-then-decompose|monte carlo em|"
    r"learning graph structures with transformer|anomaly transformer",
    re.I,
)
REJECT_TITLE_RE = re.compile(r"survey|review|forecast\b|forecasting|classification|taxonomy|benchmark", re.I)
SEQUENCE_RE = re.compile(r"\btime series\b|temporal|multivariate|sequential|sequence", re.I)
METHOD_RE = re.compile(r"anomaly|detection|deep learning|transformer|diffusion|neural|autoencoder|contrastive", re.I)

HARDCODE_PATTERNS = [
    "2510.18998",
    "2510_18998",
    "formula_006",
    "formula_010",
    "eq_6",
    "eq_10",
    "eq_12",
    "page 4",
    "page 5",
    "page 6",
    "Encode-then-Decompose",
    "Contaminated Training",
]

DEFAULT_QUERIES = [
    "time series anomaly detection deep learning",
    "multivariate time series anomaly detection transformer",
    "diffusion model time series anomaly detection",
]


def run_target_mode_eval(
    *,
    output_dir: str | Path,
    candidates: list[dict[str, Any]] | None = None,
    artifact_dirs: list[str | Path] | None = None,
    run_live_eval: bool = False,
    max_live_eval_pages: int = 3,
    full_mineru_enabled: bool = False,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    search_limitations: list[str] = []
    if candidates is None:
        candidates, search_limitations = search_candidate_metadata()

    selected_unseen = select_unseen_candidates(candidates, limit=2)
    artifact_paths = [Path(path) for path in artifact_dirs or []]
    contract_checks = [static_contract_check(path) for path in artifact_paths]
    hardcode_violations = detect_production_hardcodes(ROOT)

    live_eval = {
        "requested": run_live_eval,
        "ran": False,
        "max_pages": max_live_eval_pages,
        "limitation": "Lightweight live eval is not wired in this script; no page-level parse was performed.",
    }
    if run_live_eval:
        live_eval["status"] = "SKIPPED"
    else:
        live_eval["status"] = "NOT_REQUESTED"

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "full_mineru_enabled": full_mineru_enabled,
        "live_eval_ran": bool(live_eval["ran"]),
        "max_live_eval_pages": max_live_eval_pages,
        "candidate_count": len(candidates),
        "unseen_candidate_count": len(selected_unseen),
        "contract_bundle_count": len(contract_checks),
        "hardcode_violation_count": len(hardcode_violations),
        "status": "PASS" if len(selected_unseen) >= 2 and not hardcode_violations and all(c["status"] == "PASS" for c in contract_checks) else "FAIL",
        "limitations": search_limitations + ([live_eval["limitation"]] if run_live_eval else []),
    }
    result = {
        "summary": summary,
        "selected_unseen_candidates": selected_unseen,
        "contract_checks": contract_checks,
        "hardcode_violations": hardcode_violations,
        "live_eval": live_eval,
    }

    config = {
        "queries": DEFAULT_QUERIES,
        "excluded_ids": sorted(KNOWN_EXCLUDED_IDS),
        "full_mineru_enabled": full_mineru_enabled,
        "run_live_eval": run_live_eval,
        "max_live_eval_pages": max_live_eval_pages,
        "static_checks": [
            "candidate consistency",
            "formula_slots schema",
            "final_latex",
            "equation_group_id/group fields",
            "nearby_text",
            "crop/overlay path",
            "reference formula exclusion",
            "performance gate wording",
            "production hardcode scan",
        ],
    }
    _write_json(output_dir / "target_eval_config.json", config)
    _write_json(output_dir / "target_candidate_papers.json", candidates)
    _write_json(output_dir / "target_eval_results.json", result)
    (output_dir / "target_eval_report.md").write_text(render_target_eval_report(result), encoding="utf-8")
    (output_dir / "overfit_risk_report.md").write_text(render_overfit_risk_report(result), encoding="utf-8")
    (output_dir / "failure_cases.md").write_text(render_failure_cases(result), encoding="utf-8")
    return result


def search_candidate_metadata() -> tuple[list[dict[str, Any]], list[str]]:
    try:
        import arxiv
    except Exception as exc:
        return [], [f"arxiv package unavailable: {exc}"]

    candidates: list[dict[str, Any]] = []
    limitations: list[str] = []
    try:
        client = arxiv.Client(page_size=10, delay_seconds=0.5, num_retries=2)
        seen: set[str] = set()
        for query in DEFAULT_QUERIES:
            search = arxiv.Search(query=query, max_results=10, sort_by=arxiv.SortCriterion.Relevance)
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/abs/")[-1]
                base_id = re.sub(r"v\d+$", "", arxiv_id)
                if base_id in seen:
                    continue
                seen.add(base_id)
                candidates.append(
                    {
                        "arxiv_id": base_id,
                        "title": " ".join(result.title.split()),
                        "abstract": result.summary.strip()[:700],
                        "pdf_url": result.pdf_url or "",
                        "published": result.published.strftime("%Y-%m-%d") if result.published else "",
                        "authors": [author.name for author in (result.authors or [])[:5]],
                        "query": query,
                    }
                )
    except Exception as exc:
        limitations.append(f"metadata search failed: {exc}")
    return candidates, limitations


def select_unseen_candidates(candidates: list[dict[str, Any]], *, limit: int = 2) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        arxiv_id = str(candidate.get("arxiv_id", ""))
        title = str(candidate.get("title", ""))
        text = f"{title} {candidate.get('abstract', '')}"
        normalized_id = arxiv_id.replace("_", ".")
        if arxiv_id in KNOWN_EXCLUDED_IDS or normalized_id in KNOWN_EXCLUDED_IDS:
            continue
        if KNOWN_EXCLUDED_TITLE_RE.search(title) or REJECT_TITLE_RE.search(text):
            continue
        if not SEQUENCE_RE.search(text) or not METHOD_RE.search(text):
            continue
        item = dict(candidate)
        item["target_mode_status"] = "unseen_candidate"
        item["target_mode_score"] = _candidate_topic_score(text)
        scored.append((item["target_mode_score"], item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def static_contract_check(artifact_dir: str | Path) -> dict[str, Any]:
    artifact_dir = Path(artifact_dir)
    missing = []
    for name in [
        "canonical_paper.md",
        "document_blocks.json",
        "formula_slots.json",
        "paper_metadata.json",
        "quality_report.md",
        "performance_report.json",
    ]:
        if not (artifact_dir / name).exists():
            missing.append(name)
    if missing:
        return {"artifact_dir": str(artifact_dir), "status": "FAIL", "checks": {}, "reasons": [f"missing {missing}"]}

    canonical = (artifact_dir / "canonical_paper.md").read_text(encoding="utf-8")
    front_matter = parse_front_matter(canonical)
    document_blocks = json.loads((artifact_dir / "document_blocks.json").read_text(encoding="utf-8"))
    formula_slots = json.loads((artifact_dir / "formula_slots.json").read_text(encoding="utf-8"))
    performance_report = json.loads((artifact_dir / "performance_report.json").read_text(encoding="utf-8"))
    quality_report = (artifact_dir / "quality_report.md").read_text(encoding="utf-8")
    contract = validate_m1_contract(
        input_dir=artifact_dir,
        front_matter=front_matter,
        document_blocks=document_blocks,
        formula_slots=formula_slots,
        performance_report=performance_report,
        quality_report_markdown=quality_report,
    )
    return {"artifact_dir": str(artifact_dir), **contract}


def detect_production_hardcodes(root: str | Path = ROOT) -> list[dict[str, Any]]:
    root = Path(root)
    violations: list[dict[str, Any]] = []
    scan_roots = [root / "src", root / "scripts"]
    excluded_files = {
        root / "scripts" / "m1_target_mode_eval.py",
    }
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*.py"):
            if _is_excluded_scan_path(path, root, excluded_files):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in HARDCODE_PATTERNS:
                if pattern in text:
                    line = _line_number(text, pattern)
                    violations.append({
                        "path": str(path.relative_to(root)),
                        "line": line,
                        "pattern": pattern,
                    })
    return violations


def render_target_eval_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# M1 Target-Mode Evaluation",
        "",
        f"- status: {summary['status']}",
        f"- full_mineru_enabled: {summary['full_mineru_enabled']}",
        f"- live_eval_ran: {summary['live_eval_ran']}",
        f"- unseen_candidate_count: {summary['unseen_candidate_count']}",
        f"- hardcode_violation_count: {summary['hardcode_violation_count']}",
        "",
        "## Unseen Candidates",
        "",
    ]
    if result["selected_unseen_candidates"]:
        for candidate in result["selected_unseen_candidates"]:
            lines.append(f"- {candidate.get('arxiv_id')}: {candidate.get('title')}")
    else:
        lines.append("- none")
    lines += ["", "## Static Contract Checks", ""]
    for check in result["contract_checks"]:
        lines.append(f"- {check.get('artifact_dir')}: {check.get('status')}")
        for name, status in check.get("checks", {}).items():
            lines.append(f"  - {name}: {status}")
    lines += ["", "## Live Eval", "", f"- status: {result['live_eval']['status']}"]
    if result["summary"]["limitations"]:
        lines += ["", "## Limitations", ""]
        for limitation in result["summary"]["limitations"]:
            lines.append(f"- {limitation}")
    return "\n".join(lines)


def render_overfit_risk_report(result: dict[str, Any]) -> str:
    lines = [
        "# Overfit Risk Report",
        "",
        "## Hardcode Scan",
        "",
    ]
    if result["hardcode_violations"]:
        for violation in result["hardcode_violations"]:
            lines.append(f"- {violation['path']}:{violation['line']} contains {violation['pattern']}")
    else:
        lines.append("- No production hardcodes detected by target-mode scan.")
    lines += [
        "",
        "## Generalization Posture",
        "",
        "- This report is a target-mode static/generalization check, not proof that M1 perfectly generalizes.",
        "- Fallback reports are allowed, but do not prove the primary MinerU route is stable across all papers.",
        "- Performance WARNING remains a warning and is not promoted to PASS.",
    ]
    return "\n".join(lines)


def render_failure_cases(result: dict[str, Any]) -> str:
    failures: list[str] = []
    if result["summary"]["unseen_candidate_count"] < 2:
        failures.append("Fewer than two unseen candidates found.")
    for check in result["contract_checks"]:
        if check.get("status") != "PASS":
            failures.append(f"{check.get('artifact_dir')}: {', '.join(check.get('reasons', [])) or 'contract check failed'}")
    for violation in result["hardcode_violations"]:
        failures.append(f"{violation['path']}:{violation['line']} contains {violation['pattern']}")
    if not failures:
        failures.append("No target-mode failure cases found in this run.")
    return "# Failure Cases\n\n" + "\n".join(f"- {item}" for item in failures)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M1 target-mode static/generalization evaluation.")
    parser.add_argument("--output-dir", default=str(ROOT / "reports" / "m1_target_mode_eval"))
    parser.add_argument("--artifact-dir", action="append", default=[])
    parser.add_argument("--run-live-eval", action="store_true")
    parser.add_argument("--max-live-eval-pages", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact_dirs = args.artifact_dir or find_default_artifact_dirs(ROOT)
    result = run_target_mode_eval(
        output_dir=args.output_dir,
        artifact_dirs=artifact_dirs,
        run_live_eval=args.run_live_eval,
        max_live_eval_pages=args.max_live_eval_pages,
    )
    print(f"Target-mode eval written to: {args.output_dir}")
    print(f"Status: {result['summary']['status']}")
    print(f"Unseen candidates: {result['summary']['unseen_candidate_count']}")
    print(f"Live eval ran: {result['summary']['live_eval_ran']}")
    return 0 if result["summary"]["status"] == "PASS" else 1


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _candidate_topic_score(text: str) -> float:
    lowered = text.lower()
    score = 0.0
    weights = {
        "time series": 4.0,
        "multivariate": 2.0,
        "temporal": 1.5,
        "anomaly": 1.5,
        "detection": 1.0,
        "transformer": 1.0,
        "diffusion": 1.0,
        "deep learning": 1.0,
        "neural": 0.6,
        "autoencoder": 0.6,
        "contrastive": 0.6,
    }
    for keyword, weight in weights.items():
        if keyword in lowered:
            score += weight
    return round(score, 3)


def find_default_artifact_dirs(root: Path = ROOT) -> list[Path]:
    reports_dir = root / "reports"
    candidates = sorted(
        (
            path
            for path in reports_dir.glob("m1_acceptance_manual_review_*")
            if path.is_dir() and (path / "canonical_paper.md").exists()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[:1]


def _is_excluded_scan_path(path: Path, root: Path, excluded_files: set[Path]) -> bool:
    resolved = path.resolve()
    if any(resolved == excluded.resolve() for excluded in excluded_files):
        return True
    parts = {part.lower() for part in path.relative_to(root).parts}
    return bool({"tests", "legacy_tests", "__pycache__"} & parts)


def _line_number(text: str, pattern: str) -> int:
    before = text.split(pattern, 1)[0]
    return before.count("\n") + 1


if __name__ == "__main__":
    raise SystemExit(main())
