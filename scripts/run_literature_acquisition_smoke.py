from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from researchsensei.core.config import ConfigService  # noqa: E402


try:
    ConfigService().load()
except Exception:
    # Smoke output reports source-level failures later; local config/env loading
    # must not prevent source adapters from running with explicit environment.
    pass

from researchsensei.acquisition import ArxivAdapter, CrossrefAdapter, DBLPAdapter, FullTextResolver, OpenAlexAdapter, SemanticScholarAdapter  # noqa: E402
from researchsensei.schemas import CandidatePaper  # noqa: E402
from researchsensei.selection import SelectionService  # noqa: E402


class SearchAdapter(Protocol):
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        ...


SOURCE_ALIASES = {
    "semanticscholar": "semantic_scholar",
    "semantic-scholar": "semantic_scholar",
    "s2": "semantic_scholar",
}
SEARCH_SOURCE_ORDER = ["arxiv", "openalex", "semantic_scholar", "crossref", "dblp"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test ResearchSensei M1 literature acquisition and legal full-text discovery.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--download-top-n", type=int, default=5)
    parser.add_argument(
        "--sources",
        default="arxiv,openalex,semanticscholar,crossref,dblp,unpaywall",
        help="Comma-separated sources: arxiv,openalex,semanticscholar,crossref,dblp,unpaywall",
    )
    parser.add_argument("--workspace", default=str(ROOT / "workspace" / "literature_acquisition_smoke"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_literature_acquisition_smoke(
        query=args.query,
        max_results=args.max_results,
        download_top_n=args.download_top_n,
        sources=_parse_sources(args.sources),
        workspace=Path(args.workspace),
    )
    print("ResearchSensei literature acquisition smoke summary")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] in {"PASS", "DEGRADED_PASS"} else 2


def run_literature_acquisition_smoke(
    *,
    query: str,
    max_results: int,
    download_top_n: int,
    sources: list[str],
    workspace: Path,
    adapters: dict[str, SearchAdapter] | None = None,
    fulltext_resolver: FullTextResolver | None = None,
) -> dict[str, Any]:
    adapters = adapters or _default_adapters()
    source_metrics: list[dict[str, Any]] = []
    warnings: list[str] = []
    candidates: list[CandidatePaper] = []

    for source in [source for source in SEARCH_SOURCE_ORDER if source in sources]:
        started = time.perf_counter()
        adapter = adapters.get(source)
        if adapter is None:
            source_metrics.append(_metric(source, True, False, 0, started, "adapter not configured"))
            warnings.append(f"ACQUISITION_FAILED:{source}: adapter not configured")
            continue
        try:
            results = adapter.search(query, max_results=max_results)
            candidates.extend(results)
            source_metrics.append(_metric(source, True, True, len(results), started, ""))
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
            source_metrics.append(_metric(source, True, False, 0, started, error))
            warnings.append(f"ACQUISITION_FAILED:{source}: {error}")

    selection = SelectionService()
    deduplicated = selection.deduplicate(candidates)
    resolver = fulltext_resolver or FullTextResolver(timeout_seconds=30.0)
    resolved, fulltext_metrics = resolver.resolve_many(
        deduplicated,
        download_top_n=download_top_n,
        workspace=workspace / _safe_name(query),
    )
    if "unpaywall" in sources:
        source_metrics.extend(fulltext_metrics)

    summary = _summary(query, sources, source_metrics, candidates, resolved, warnings)
    summary["top_candidates"] = [_candidate_row(candidate) for candidate in resolved[:20]]
    summary["verdict"] = _verdict(summary)
    return summary


def _summary(
    query: str,
    sources: list[str],
    source_metrics: list[dict[str, Any]],
    raw_candidates: list[CandidatePaper],
    candidates: list[CandidatePaper],
    warnings: list[str],
) -> dict[str, Any]:
    status_counts = Counter(candidate.fulltext_status for candidate in candidates)
    selected_source_counts = Counter(candidate.selected_fulltext_source or "metadata_only" for candidate in candidates)
    failure_counts = Counter(
        candidate.fulltext_failure_reason
        for candidate in candidates
        if candidate.fulltext_failure_reason
    )
    source_counts = _source_counts(source_metrics)
    non_arxiv = [
        candidate for candidate in candidates
        if "arxiv" not in set(candidate.sources or ([candidate.source] if candidate.source else []))
    ]
    return {
        "query": query,
        "sources_requested": sources,
        "source_metrics": source_counts,
        "attempted_sources": sorted(source_counts),
        "raw_candidate_count": len(raw_candidates),
        "total_candidates": len(candidates),
        "non_arxiv_candidates": len(non_arxiv),
        "doi_count": sum(1 for candidate in candidates if candidate.doi),
        "arxiv_id_count": sum(1 for candidate in candidates if candidate.arxiv_id),
        "legal_fulltext_count": sum(1 for candidate in candidates if candidate.fulltext_status in {"source_ready", "pdf_ready", "html_ready"}),
        "source_ready_count": status_counts.get("source_ready", 0),
        "pdf_ready_count": status_counts.get("pdf_ready", 0),
        "html_ready_count": status_counts.get("html_ready", 0),
        "metadata_only_count": status_counts.get("metadata_only", 0),
        "metadata_only_after_unpaywall_count": sum(1 for candidate in candidates if candidate.doi and candidate.fulltext_status == "metadata_only"),
        "failed_count": status_counts.get("failed", 0),
        "selected_fulltext_source_counts": dict(selected_source_counts.most_common()),
        "oa_pdf_found_count": sum(
            selected_source_counts.get(source, 0)
            for source in ("openalex_oa_pdf", "semantic_scholar_oa_pdf", "publisher_oa_pdf", "repository_pdf")
        ),
        "repository_pdf_count": selected_source_counts.get("repository_pdf", 0),
        "publisher_oa_count": selected_source_counts.get("publisher_oa_pdf", 0),
        "failure_reasons": dict(failure_counts.most_common(8)),
        "warnings": warnings,
    }


def _candidate_row(candidate: CandidatePaper) -> dict[str, Any]:
    return {
        "title": candidate.title,
        "year": candidate.year,
        "venue": candidate.venue,
        "discovery_sources": candidate.sources or ([candidate.source] if candidate.source else []),
        "doi": candidate.doi,
        "arxiv_id": candidate.arxiv_id,
        "landing_url": candidate.landing_url or candidate.url,
        "candidate_pdf_urls": candidate.candidate_pdf_urls[:3],
        "candidate_source_urls": candidate.candidate_source_urls[:3],
        "selected_fulltext_source": candidate.selected_fulltext_source,
        "fulltext_status": candidate.fulltext_status,
        "fulltext_failure_reason": candidate.fulltext_failure_reason,
        "can_deep_read": candidate.can_deep_read,
        "needs_user_upload": candidate.needs_user_upload,
    }


def _source_counts(metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        source = str(metric.get("source") or "unknown")
        bucket = result.setdefault(source, {"attempted": False, "success_count": 0, "failure_count": 0, "count": 0, "errors": []})
        bucket["attempted"] = bool(bucket["attempted"] or metric.get("attempted"))
        if metric.get("success"):
            bucket["success_count"] = int(bucket["success_count"]) + 1
        else:
            bucket["failure_count"] = int(bucket["failure_count"]) + 1
            error = str(metric.get("error") or "")
            if error and error not in bucket["errors"] and len(bucket["errors"]) < 5:
                bucket["errors"].append(error)
        bucket["count"] = int(bucket["count"]) + int(metric.get("count") or 0)
    return result


def _verdict(summary: dict[str, Any]) -> str:
    if summary["total_candidates"] <= 0:
        return "FAIL"
    if summary["legal_fulltext_count"] <= 0:
        return "DEGRADED_PASS"
    return "PASS" if summary["source_ready_count"] or summary["pdf_ready_count"] else "DEGRADED_PASS"


def _metric(source: str, attempted: bool, success: bool, count: int, started: float, error: str) -> dict[str, Any]:
    return {
        "source": source,
        "attempted": attempted,
        "success": success,
        "count": count,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "error": error,
    }


def _parse_sources(value: str) -> list[str]:
    parsed = []
    for raw in value.split(","):
        source = SOURCE_ALIASES.get(raw.strip().lower(), raw.strip().lower())
        if source and source not in parsed:
            parsed.append(source)
    return parsed


def _default_adapters() -> dict[str, SearchAdapter]:
    return {
        "arxiv": ArxivAdapter(timeout=12.0),
        "openalex": OpenAlexAdapter(),
        "semantic_scholar": SemanticScholarAdapter(timeout=12.0),
        "crossref": CrossrefAdapter(),
        "dblp": DBLPAdapter(timeout=12.0),
    }


def _safe_name(value: str) -> str:
    import re

    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return safe[:80] or "query"


if __name__ == "__main__":
    raise SystemExit(main())
