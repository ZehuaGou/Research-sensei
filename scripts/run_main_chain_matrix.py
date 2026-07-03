from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import queue
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from starlette.testclient import TestClient

from researchsensei.core.env_loader import load_runtime_env
from researchsensei.web.app import create_app

# Import acceptance helpers as a module so cache helpers and utilities are available.
sys.path.insert(0, str(ROOT / "scripts"))
import run_main_chain_acceptance as acceptance  # noqa: E402

DEFAULT_QUERIES = [
    "time series anomaly detection",
    "multivariate time series imputation",
    "graph anomaly detection",
    "graph neural network anomaly detection",
    "transformer time series anomaly detection",
    "diffusion models for time series imputation",
    "time series forecasting",
    "anomaly detection survey",
    "graph neural network time series",
    "diffusion models for forecasting",
    "transformer forecasting anomaly detection",
    "multivariate time series forecasting",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ResearchSensei M1->M2->M3 main-chain regression matrix."
    )
    parser.add_argument("--provider", default="cc_switch")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--use-cache", action="store_true", help="Use cached direction search results when available.")
    parser.add_argument("--refresh-cache", action="store_true", help="Force refresh cache even if valid entry exists.")
    parser.add_argument("--cache-dir", default=str(ROOT / ".cache" / "researchsensei"), help="Cache directory for direction search results.")
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--workspace", default=str(ROOT / "workspace" / "main_chain_matrix"))
    parser.add_argument("--output-json", default=str(ROOT / "workspace" / "main_chain_matrix" / "summary.json"), help="Output JSON summary path.")
    parser.add_argument("--queries", nargs="*", default=None, help="Override default queries. If not provided, uses 12 default regression queries.")
    parser.add_argument("--max-failures", type=int, default=0, help="Maximum allowed FAIL rows before matrix exits non-zero. Default 0.")
    parser.add_argument(
        "--query-timeout-seconds",
        type=float,
        default=240.0,
        help="Hard timeout per query. Use 0 to disable subprocess isolation.",
    )
    parser.add_argument(
        "--llm-card-timeout-seconds",
        type=float,
        default=30.0,
        help="Override per-card LLM timeout for matrix runs. Use 0 for application default.",
    )
    return parser.parse_args(argv)


def _resolve_llm_mode(provider: str, skip_llm: bool) -> dict[str, object]:
    return acceptance.resolve_llm_mode(provider=provider, skip_llm=skip_llm)


def _classify_failure_root_cause(row: dict[str, Any]) -> str:
    """Classify the root cause of a non-SUCCESS result."""
    verdict = row.get("final_verdict", "")
    stage = row.get("failed_stage", "")
    status = row.get("final_understanding_status", "")
    blocking = row.get("blocking_reason", "")
    source_strategy = row.get("source_strategy", "")

    if verdict == "FAIL":
        if stage == "direction_search":
            if status or blocking:
                return "direction_search_failed"
            return "direction_search_no_candidates"
        if stage == "seed_expansion":
            return "seed_expansion_no_handoff"
        if stage == "deep_read":
            return f"deep_read_failed:{blocking or status}"
        if stage == "query_timeout":
            return "query_timeout"
        if status == "BASELINE_ONLY":
            return "llm_not_configured"
        return f"pipeline_failed:{stage or status}"

    if verdict == "BLOCKED":
        return f"blocked:{blocking}"

    if verdict == "DEGRADED":
        if status == "DEGRADED_STRUCTURAL":
            components = row.get("returned_card_components", [])
            if "paper_card" not in components:
                return "degraded_paper_card_not_returned"
            if blocking == "FORMULA_DERIVATION_BLOCKED":
                return f"degraded_formula_derivation_blocked:{blocking}"
            if "formula_cards" not in components:
                return "degraded_formula_derivation_blocked"
            return f"degraded:{blocking or 'unknown'}"
        return f"degraded_unknown:{status}"

    return f"unexpected:{verdict}"


def _source_metrics_summary(metrics_by_source: dict[str, Any]) -> dict[str, int]:
    """Extract compact source metrics: attempted count per source."""
    return {source: 1 for source in metrics_by_source if metrics_by_source.get(source, {}).get("attempted")}


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    queries = args.queries if args.queries else DEFAULT_QUERIES
    llm_mode = _resolve_llm_mode(provider=args.provider, skip_llm=args.skip_llm)

    rows: list[dict[str, Any]] = []
    cache_hits = 0
    start_time = time.perf_counter()

    for i, query in enumerate(queries):
        qstart = time.perf_counter()
        print(f"[{i+1}/{len(queries)}] {query} ... ", end="", flush=True)

        result = _run_query_with_timeout(
            args,
            query=query,
            llm_mode=llm_mode,
        )

        if result.get("cache_hit", False):
            cache_hits += 1

        elapsed_ms = int((time.perf_counter() - qstart) * 1000)

        row = _build_row(result, elapsed_ms)
        rows.append(row)

        verdict = result.get("final_verdict", "FAIL")
        status = result.get("final_understanding_status", "")
        print(f"{verdict} ({status}, {elapsed_ms}ms)")

    total_time_s = round(time.perf_counter() - start_time, 1)

    summary = _build_summary(rows, args, cache_hits, total_time_s, llm_mode)
    return summary


def _run_query_with_timeout(
    args: argparse.Namespace,
    *,
    query: str,
    llm_mode: dict[str, object],
) -> dict[str, Any]:
    timeout_seconds = float(args.query_timeout_seconds or 0)
    payload = _query_payload(args, query, llm_mode)
    if timeout_seconds <= 0:
        return _run_query_direct(payload)

    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(target=_query_worker, args=(payload, result_queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return _timeout_result(query, llm_mode, timeout_seconds)

    try:
        message = result_queue.get_nowait()
    except queue.Empty:
        return _worker_failed_result(query, llm_mode, "Acceptance worker exited without returning a result.")

    if not isinstance(message, dict) or not message.get("ok"):
        error = str((message or {}).get("error") if isinstance(message, dict) else message)
        return _worker_failed_result(query, llm_mode, error or "Acceptance worker failed.")
    result = message.get("result")
    if isinstance(result, dict):
        return result
    return _worker_failed_result(query, llm_mode, "Acceptance worker returned a non-object result.")


def _query_payload(args: argparse.Namespace, query: str, llm_mode: dict[str, object]) -> dict[str, Any]:
    return {
        "query": query,
        "provider": args.provider,
        "workspace": args.workspace,
        "max_candidates": args.max_candidates,
        "cache_dir": args.cache_dir,
        "use_cache": args.use_cache,
        "refresh_cache": args.refresh_cache,
        "llm_card_timeout_seconds": float(args.llm_card_timeout_seconds or 0),
        "llm_enabled": bool(llm_mode["enabled"]),
        "llm_mode_note": str(llm_mode["note"]),
    }


def _query_worker(payload: dict[str, Any], result_queue: Any) -> None:
    try:
        result_queue.put({"ok": True, "result": _run_query_direct(payload)})
    except Exception as exc:
        result_queue.put({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})


def _run_query_direct(payload: dict[str, Any]) -> dict[str, Any]:
    card_timeout = float(payload.get("llm_card_timeout_seconds") or 0)
    if card_timeout > 0:
        os.environ["RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS"] = str(card_timeout)
    client = TestClient(
        create_app(
            workspace_root=str(payload["workspace"]),
            enable_configured_llm=bool(payload["llm_enabled"]),
            llm_provider=str(payload["provider"]) if payload["llm_enabled"] else "",
        )
    )
    return acceptance.run_main_chain_acceptance(
        client,
        query=str(payload["query"]),
        max_candidates=int(payload["max_candidates"]),
        llm_enabled=bool(payload["llm_enabled"]),
        llm_mode_note=str(payload["llm_mode_note"]),
        cache_dir=str(payload["cache_dir"]),
        use_cache=bool(payload["use_cache"]),
        refresh_cache=bool(payload["refresh_cache"]),
    )


def _timeout_result(query: str, llm_mode: dict[str, object], timeout_seconds: float) -> dict[str, Any]:
    message = f"Main-chain query exceeded {timeout_seconds:.0f}s and was terminated."
    return _failed_query_result(
        query,
        llm_mode,
        stage="query_timeout",
        message=message,
        warnings=[f"QUERY_TIMEOUT:{timeout_seconds:.0f}s"],
    )


def _worker_failed_result(query: str, llm_mode: dict[str, object], error: str) -> dict[str, Any]:
    message = f"Main-chain acceptance worker failed: {error}"
    return _failed_query_result(
        query,
        llm_mode,
        stage="worker_error",
        message=message,
        warnings=["ACCEPTANCE_WORKER_FAILED"],
    )


def _failed_query_result(
    query: str,
    llm_mode: dict[str, object],
    *,
    stage: str,
    message: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "query": query,
        "llm_enabled": bool(llm_mode["enabled"]),
        "llm_mode_note": str(llm_mode["note"]),
        "cache_hit": False,
        "failed_stage": stage,
        "message": message,
        "selected_candidate_title": "",
        "selected_candidate_arxiv_id": "",
        "selected_candidate_sources": [],
        "selected_seed_handoff_title": "",
        "selected_seed_handoff_arxiv_id": "",
        "selected_seed_handoff_sources": [],
        "selected_input_type": "unknown",
        "source_strategy": "unknown",
        "arxiv_source_downloaded": False,
        "fallback_used": "",
        "seed_expansion_status": "",
        "seed_expansion_group_counts": {"upstream": 0, "downstream": 0, "same_route": 0, "surveys": 0},
        "direction_source_metrics": {},
        "seed_source_metrics": {},
        "handoff_job_id": "",
        "final_understanding_status": "",
        "blocking_reason": "",
        "cards_status_code": 0,
        "returned_card_components": [],
        "formula_origin_summary": {},
        "warnings": warnings,
        "final_verdict": "FAIL",
        "verdict_reasons": [message],
    }


def _build_row(result: dict[str, Any], elapsed_ms: int) -> dict[str, Any]:
    selected_candidate = {}
    selected_candidate["title"] = result.get("selected_candidate_title", "")
    selected_candidate["arxiv_id"] = result.get("selected_candidate_arxiv_id", "")
    selected_candidate["sources"] = result.get("selected_candidate_sources", [])

    handoff = {}
    handoff["title"] = result.get("selected_seed_handoff_title", "")
    handoff["arxiv_id"] = result.get("selected_seed_handoff_arxiv_id", "")
    handoff["sources"] = result.get("selected_seed_handoff_sources", [])

    # Identify arxiv_id/doi/pdf_url from handoff or direction candidate
    arxiv_id = handoff.get("arxiv_id", "") or selected_candidate.get("arxiv_id", "")
    doi = ""
    pdf_url = ""

    input_type = result.get("selected_input_type", "unknown")
    source_strategy = result.get("source_strategy", "unknown")
    final_status = result.get("final_understanding_status", "")
    blocking_reason = result.get("blocking_reason", "")
    cards_code = result.get("cards_status_code", 0)
    components = result.get("returned_card_components", [])
    verdict = result.get("final_verdict", "FAIL")
    cache_hit = result.get("cache_hit", False)
    source_metrics = result.get("direction_source_metrics", {})
    formula_origin = result.get("formula_origin_summary", {})
    warnings = result.get("warnings", [])

    failure_root_cause = _classify_failure_root_cause(result)

    row: dict[str, Any] = {
        "query": result.get("query", ""),
        "selected_candidate": selected_candidate,
        "handoff_candidate": handoff,
        "arxiv_id": arxiv_id,
        "doi": doi,
        "pdf_url": pdf_url,
        "input_type": input_type,
        "source_strategy": source_strategy,
        "final_status": final_status,
        "blocking_reason": blocking_reason,
        "cards_code": cards_code,
        "components": components,
        "formula_origin_summary": formula_origin,
        "verdict": verdict,
        "cache_hit": cache_hit,
        "source_metrics": _source_metrics_summary(source_metrics),
        "failure_root_cause": failure_root_cause,
        "warnings": warnings,
        "elapsed_ms": elapsed_ms,
        "seed_expansion_status": result.get("seed_expansion_status", ""),
        "seed_expansion_group_counts": result.get("seed_expansion_group_counts", {}),
        "arxiv_source_downloaded": result.get("arxiv_source_downloaded", False),
        "fallback_used": result.get("fallback_used", ""),
        "handoff_job_id": result.get("handoff_job_id", ""),
    }
    return row


def _build_summary(
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    cache_hits: int,
    total_time_s: float,
    llm_mode: dict[str, object],
) -> dict[str, Any]:
    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    degraded = sum(1 for r in rows if r["verdict"] == "DEGRADED")
    blocked = sum(1 for r in rows if r["verdict"] == "BLOCKED")
    failed = sum(1 for r in rows if r["verdict"] == "FAIL")
    success_count = sum(1 for r in rows if r["final_status"] == "SUCCESS")
    degraded_count = sum(1 for r in rows if r["final_status"] == "DEGRADED_STRUCTURAL")
    blocked_count = sum(1 for r in rows if r["final_status"] == "BLOCKED_UNDERSTANDING")
    baseline_count = sum(1 for r in rows if r["final_status"] == "BASELINE_ONLY")

    # Root cause breakdown
    root_causes: dict[str, int] = {}
    for r in rows:
        rc = r["failure_root_cause"]
        root_causes[rc] = root_causes.get(rc, 0) + 1

    summary: dict[str, Any] = {
        "schema_version": "main_chain_matrix_v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": args.provider,
        "llm_enabled": bool(llm_mode["enabled"]),
        "llm_mode_note": str(llm_mode["note"]),
        "cache_enabled": bool(args.use_cache or args.refresh_cache),
        "cache_refreshed": args.refresh_cache,
        "cache_hits": cache_hits,
        "query_timeout_seconds": float(args.query_timeout_seconds or 0),
        "llm_card_timeout_seconds": float(args.llm_card_timeout_seconds or 0),
        "total_queries": len(rows),
        "passed": passed,
        "degraded": degraded,
        "blocked": blocked,
        "failed": failed,
        "final_status_breakdown": {
            "SUCCESS": success_count,
            "DEGRADED_STRUCTURAL": degraded_count,
            "BLOCKED_UNDERSTANDING": blocked_count,
            "BASELINE_ONLY": baseline_count,
        },
        "failure_root_cause_breakdown": root_causes,
        "total_time_seconds": total_time_s,
        "rows": rows,
    }
    return summary


def print_table(summary: dict[str, Any]) -> None:
    rows = summary["rows"]
    print()
    print("=" * 120)
    print(f"MAIN CHAIN MATRIX  |  provider={summary['provider']}  "
          f"cache={'Y' if summary['cache_enabled'] else 'N'}  "
          f"cache_hits={summary['cache_hits']}  "
          f"llm={'Y' if summary['llm_enabled'] else 'N'}")
    print("=" * 120)
    header = f"{'#':>3}  {'VERDICT':<16}  {'STATUS':<24}  {'CARDS':<5}  {'STRATEGY':<16}  {'ROOT CAUSE':<32}  QUERY"
    print(header)
    print("-" * 120)
    for i, row in enumerate(rows):
        verdict = row["verdict"]
        status = row["final_status"][:24]
        cards = str(row["cards_code"])
        strategy = row["source_strategy"][:16]
        rc = row["failure_root_cause"][:32]
        query = row["query"][:30]
        tag = "C" if row.get("cache_hit") else " "
        print(f"{i+1:>3}  {verdict:<16}  {status:<24}  {cards:<5}  {strategy:<16}  {rc:<32}  {tag} {query}")
    print("-" * 120)
    d = summary["final_status_breakdown"]
    print(f"  PASS={summary['passed']}  DEGRADED={summary.get('degraded', 0)}  BLOCKED={summary.get('blocked', 0)}  FAIL={summary['failed']}  "
          f"cache_hits={summary['cache_hits']}/{summary['total_queries']}  "
          f"total_time={summary['total_time_seconds']}s")
    print(f"  SUCCESS={d['SUCCESS']}  DEGRADED_STRUCTURAL={d['DEGRADED_STRUCTURAL']}  "
          f"BLOCKED_UNDERSTANDING={d['BLOCKED_UNDERSTANDING']}  "
          f"BASELINE={d['BASELINE_ONLY']}")
    if summary.get("failure_root_cause_breakdown"):
        print(f"  Root causes: {summary['failure_root_cause_breakdown']}")
    print()


def _exit_code_for_summary(summary: dict[str, Any], max_failures: int) -> tuple[int, str]:
    if int(summary.get("total_queries") or 0) == 0:
        return 2, "ERROR: No rows produced."
    failed = int(summary.get("failed") or 0)
    if failed > max_failures:
        return 2, f"ERROR: {failed} FAIL rows exceeds max-failures={max_failures}"
    return 0, ""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env_loaded = load_runtime_env(suppress_errors=True)
    if env_loaded:
        print(f"[env] loaded from .env: {env_loaded}")
    summary = run_matrix(args)

    # Print table
    print_table(summary)

    # Ensure output directory
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote matrix summary to {output_path}")

    # Exit code
    exit_code, error = _exit_code_for_summary(summary, args.max_failures)
    if error:
        print(error)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
