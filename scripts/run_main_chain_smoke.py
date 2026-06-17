from __future__ import annotations

import argparse
import json
import os
import re
import sys
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

from starlette.testclient import TestClient  # noqa: E402

from researchsensei.core.config import ConfigService  # noqa: E402
from researchsensei.web.app import create_app  # noqa: E402


SUCCESS_STATUSES = {"SUCCESS", "DEGRADED_STRUCTURAL", "BLOCKED_UNDERSTANDING"}
CARD_COMPONENTS = {"paper_card", "formula_cards", "teaching_cards"}


class ResponseLike(Protocol):
    status_code: int

    def json(self) -> dict[str, Any]:
        ...


class ClientLike(Protocol):
    def post(self, url: str, *, json: dict[str, Any]) -> ResponseLike:
        ...

    def get(self, url: str) -> ResponseLike:
        ...


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ResearchSensei M1 -> M2 -> M3 main-chain smoke through local API handlers."
    )
    parser.add_argument("--query", default="time series anomaly detection")
    parser.add_argument("--provider", default="mimo")
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--workspace", default=str(ROOT / "workspace" / "main_chain_smoke"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    llm_mode = resolve_llm_mode(provider=args.provider, skip_llm=args.skip_llm)
    client = TestClient(
        create_app(
            workspace_root=args.workspace,
            enable_configured_llm=llm_mode["enabled"],
            llm_provider=args.provider if llm_mode["enabled"] else "",
        )
    )
    result = run_main_chain_smoke(
        client,
        query=args.query,
        max_candidates=args.max_candidates,
        llm_enabled=bool(llm_mode["enabled"]),
        llm_mode_note=str(llm_mode["note"]),
    )
    print_summary(result)
    return 0 if result["final_verdict"] in {"PASS", "DEGRADED_PASS"} else 2


def resolve_llm_mode(*, provider: str, skip_llm: bool) -> dict[str, object]:
    config = ConfigService().load()
    if skip_llm:
        return {"enabled": False, "note": "LLM disabled by --skip-llm; expecting BASELINE_ONLY."}
    if not _env_truthy("RESEARCHSENSEI_ENABLE_API_LLM"):
        return {
            "enabled": False,
            "note": "RESEARCHSENSEI_ENABLE_API_LLM is not enabled; running no-LLM smoke and expecting BASELINE_ONLY.",
        }
    if provider not in config.providers:
        raise SystemExit(f"ERROR: unknown LLM provider '{provider}'. Configure it in config/local.toml or config/sensei.example.toml.")
    provider_config = config.providers[provider]
    if provider_config.api_key_env and not os.getenv(provider_config.api_key_env, ""):
        return {
            "enabled": False,
            "note": f"{provider_config.api_key_env} is missing; running no-LLM smoke and expecting BASELINE_ONLY.",
        }
    return {"enabled": True, "note": f"LLM enabled with provider '{provider}'."}


def run_main_chain_smoke(
    client: ClientLike,
    *,
    query: str,
    max_candidates: int,
    llm_enabled: bool,
    llm_mode_note: str = "",
) -> dict[str, Any]:
    warnings: list[str] = []
    direction_response = _request_json(
        client.post("/api/v1/directions/search", json={"query": query}),
        "direction search",
    )
    direction_source_metrics = direction_response.get("source_metrics") or []
    direction_papers = _papers(direction_response)
    # Search all direction papers for the best arXiv candidate (don't truncate
    # before selection — arXiv papers may be ranked after OpenAlex results).
    direction_candidate = _select_arxiv_candidate(direction_papers, query=query)
    if not direction_candidate:
        return _fail(
            query=query,
            llm_enabled=llm_enabled,
            llm_mode_note=llm_mode_note,
            stage="direction_search",
            message="No arXiv candidate was returned by direction search.",
            warnings=warnings + _warnings(direction_response),
            source_metrics=direction_source_metrics,
        )

    seed_response = _request_json(
        client.post("/api/v1/directions/seed_expansion", json={"seed": direction_candidate}),
        "seed expansion",
    )
    warnings.extend(_warnings(direction_response))
    warnings.extend(_warnings(seed_response))
    seed_candidates = _seed_candidates(seed_response)
    handoff_candidate = _select_handoff_candidate(seed_candidates[:max(1, max_candidates)], query=query)

    # Fallback: if seed expansion found no source-backed handoff, try the
    # direction candidate itself if it has a handoff source.
    if not handoff_candidate and _has_handoff_source(direction_candidate):
        handoff_candidate = direction_candidate
        warnings.append("SEED_EXPANSION_FALLBACK_TO_DIRECTION_CANDIDATE")

    if not handoff_candidate:
        # Second fallback: try the best direction paper with any source (including DOI)
        best_dir = _select_best_source_candidate(direction_papers, query=query)
        if best_dir:
            handoff_candidate = best_dir
            warnings.append("DIRECTION_CANDIDATE_FALLBACK_BEST_SOURCE")

    if not handoff_candidate:
        return _fail(
            query=query,
            llm_enabled=llm_enabled,
            llm_mode_note=llm_mode_note,
            stage="seed_expansion",
            message="Seed expansion returned no source-backed handoff candidate.",
            selected_candidate=direction_candidate,
            seed_response=seed_response,
            warnings=warnings,
        )

    handoff_raw_response = client.post("/api/v1/directions/deep_read", json={"candidate": _handoff_payload(handoff_candidate)})
    handoff_response = _safe_json(handoff_raw_response)
    if handoff_raw_response.status_code >= 400:
        detail = handoff_response.get("detail") if isinstance(handoff_response, dict) else {}
        if not isinstance(detail, dict):
            detail = handoff_response
        source_status = detail.get("source_status") if isinstance(detail.get("source_status"), dict) else {}
        return _fail(
            query=query,
            llm_enabled=llm_enabled,
            llm_mode_note=llm_mode_note,
            stage="deep_read",
            message=str(detail.get("message") or detail.get("status") or "Deep-read handoff failed."),
            selected_candidate=handoff_candidate,
            seed_response=seed_response,
            warnings=warnings,
            source_metrics=direction_source_metrics,
            handoff_job_id=str(detail.get("job_id") or ""),
            selected_input_type=_selected_input_type(source_status),
            source_strategy=_source_strategy(source_status),
        )
    source_status = handoff_response.get("source_status") if isinstance(handoff_response.get("source_status"), dict) else {}
    job_id = str(handoff_response.get("job_id") or "")
    if not job_id:
        return _fail(
            query=query,
            llm_enabled=llm_enabled,
            llm_mode_note=llm_mode_note,
            stage="deep_read",
            message="Deep-read handoff did not return a job_id.",
            selected_candidate=handoff_candidate,
            seed_response=seed_response,
            warnings=warnings,
            source_metrics=direction_source_metrics,
        )

    status_response = _request_json(client.get(f"/api/v1/jobs/{job_id}/understanding_status"), "understanding status")
    understanding_status = status_response.get("understanding_status") or {}
    if not isinstance(understanding_status, dict):
        understanding_status = {}
    paper_workspace_status = status_response.get("paper_workspace_status") or {}
    if not isinstance(paper_workspace_status, dict):
        paper_workspace_status = {}
    final_status = str(understanding_status.get("status") or "")

    cards_raw_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    cards_status_code = cards_raw_response.status_code
    cards_payload = _safe_json(cards_raw_response)
    cards = cards_payload.get("cards") if isinstance(cards_payload, dict) else {}
    returned_components = sorted((cards or {}).keys()) if isinstance(cards, dict) else []

    final_verdict, verdict_reasons = evaluate_gating(
        final_status=final_status,
        cards_status_code=cards_status_code,
        returned_components=returned_components,
        understanding_status=understanding_status,
        llm_enabled=llm_enabled,
    )

    return {
        "query": query,
        "llm_enabled": llm_enabled,
        "llm_mode_note": llm_mode_note,
        "selected_candidate_title": str(direction_candidate.get("title") or ""),
        "selected_candidate_arxiv_id": _candidate_arxiv_id(direction_candidate),
        "selected_candidate_sources": _candidate_sources(direction_candidate),
        "selected_seed_handoff_title": str(handoff_candidate.get("title") or ""),
        "selected_seed_handoff_arxiv_id": _candidate_arxiv_id(handoff_candidate),
        "selected_seed_handoff_sources": _candidate_sources(handoff_candidate),
        "selected_input_type": _selected_input_type(source_status),
        "source_strategy": _source_strategy(source_status),
        "arxiv_source_downloaded": bool(source_status.get("latex_source_available") or source_status.get("latex_source_path")),
        "fallback_used": source_status.get("fallback_used", ""),
        "seed_expansion_status": seed_response.get("seed_expansion_status") or seed_response.get("status") or "",
        "seed_expansion_group_counts": seed_group_counts(seed_response),
        "direction_source_metrics": _source_metrics_by_source(direction_source_metrics),
        "seed_source_metrics": _seed_metrics_by_source(seed_response.get("source_metrics") or []),
        "handoff_job_id": job_id,
        "final_understanding_status": final_status,
        "blocking_reason": understanding_status.get("blocking_reason", ""),
        "cards_status_code": cards_status_code,
        "returned_card_components": returned_components,
        "formula_origin_summary": _formula_origin_summary(paper_workspace_status),
        "warnings": warnings,
        "final_verdict": final_verdict,
        "verdict_reasons": verdict_reasons,
    }


def evaluate_gating(
    *,
    final_status: str,
    cards_status_code: int,
    returned_components: list[str],
    understanding_status: dict[str, Any],
    llm_enabled: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    component_status = understanding_status.get("component_status") or {}
    if not isinstance(component_status, dict):
        component_status = {}

    if not llm_enabled:
        if final_status != "BASELINE_ONLY":
            reasons.append(f"no-LLM smoke expected BASELINE_ONLY, got {final_status}")
        if cards_status_code != 403:
            reasons.append(f"BASELINE_ONLY cards endpoint must be 403, got {cards_status_code}")
        return ("DEGRADED_PASS" if not reasons else "FAIL", reasons)

    if final_status == "BASELINE_ONLY":
        reasons.append("LLM was enabled, but final status is BASELINE_ONLY; likely API LLM configuration failed.")
        return "FAIL", reasons
    if final_status not in SUCCESS_STATUSES:
        reasons.append(f"unexpected final understanding_status: {final_status}")
        return "FAIL", reasons

    if final_status == "SUCCESS":
        if cards_status_code != 200:
            reasons.append(f"SUCCESS cards endpoint must be 200, got {cards_status_code}")
        missing = sorted(CARD_COMPONENTS - set(returned_components))
        if missing:
            reasons.append(f"SUCCESS cards missing components: {missing}")
        return ("PASS" if not reasons else "FAIL", reasons)

    if final_status == "DEGRADED_STRUCTURAL":
        if cards_status_code != 200:
            reasons.append(f"DEGRADED_STRUCTURAL cards endpoint must be 200, got {cards_status_code}")
        non_success = [
            component for component in returned_components
            if str(component_status.get(component) or "").upper() != "SUCCESS"
        ]
        if non_success:
            reasons.append(f"DEGRADED cards returned non-success components: {non_success}")
        if not returned_components:
            reasons.append("DEGRADED cards returned no successful components")
        return ("DEGRADED_PASS" if not reasons else "FAIL", reasons)

    if final_status == "BLOCKED_UNDERSTANDING":
        if cards_status_code != 403:
            reasons.append(f"BLOCKED_UNDERSTANDING cards endpoint must be 403, got {cards_status_code}")
        return ("DEGRADED_PASS" if not reasons else "FAIL", reasons)

    return "FAIL", [f"unhandled final status: {final_status}"]


def seed_group_counts(seed_response: dict[str, Any]) -> dict[str, int]:
    return {
        "upstream": len(seed_response.get("upstream_papers") or []),
        "downstream": len(seed_response.get("downstream_papers") or []),
        "same_route": len(seed_response.get("same_route_papers") or []),
        "surveys": len(seed_response.get("related_surveys") or []),
    }


def _source_metrics_by_source(metrics: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(metrics, list):
        return result
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        source = str(metric.get("source") or "unknown")
        result[source] = {
            "attempted": bool(metric.get("attempted")),
            "success": bool(metric.get("success")),
            "count": int(metric.get("count") or 0),
            "latency_ms": int(metric.get("latency_ms") or 0),
            "error": str(metric.get("error") or ""),
        }
    return result


def _seed_metrics_by_source(metrics: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(metrics, list):
        return result
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        source = str(metric.get("source") or "unknown")
        bucket = result.setdefault(source, {"attempted": False, "success_count": 0, "failure_count": 0, "count": 0})
        bucket["attempted"] = bool(bucket["attempted"] or metric.get("attempted"))
        if metric.get("success"):
            bucket["success_count"] = int(bucket["success_count"]) + 1
        else:
            bucket["failure_count"] = int(bucket["failure_count"]) + 1
        bucket["count"] = int(bucket["count"]) + int(metric.get("count") or 0)
    return result


def print_summary(result: dict[str, Any]) -> None:
    print("ResearchSensei main-chain smoke summary")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _papers(response: dict[str, Any]) -> list[dict[str, Any]]:
    papers = response.get("papers") or response.get("candidate_cards") or []
    return [paper for paper in papers if isinstance(paper, dict)]


def _select_arxiv_candidate(candidates: list[dict[str, Any]], *, query: str = "") -> dict[str, Any] | None:
    """Select the best arXiv candidate, preferring query-relevant method papers over surveys."""
    arxiv_candidates = []
    for candidate in candidates:
        arxiv_id = candidate.get("arxiv_id") or _candidate_arxiv_id(candidate)
        if arxiv_id:
            arxiv_candidates.append(candidate)
    if not arxiv_candidates:
        return None
    if not query or len(arxiv_candidates) == 1:
        return arxiv_candidates[0]
    query_terms = _query_terms(query)
    scored = [
        (_candidate_relevance_score(c, query_terms=query_terms), i, c)
        for i, c in enumerate(arxiv_candidates)
    ]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    return scored[0][2]


def _select_best_source_candidate(candidates: list[dict[str, Any]], *, query: str = "") -> dict[str, Any] | None:
    """Select the best candidate with any source (arxiv, pdf_url, doi), preferring relevance."""
    query_terms = _query_terms(query)
    scored = [
        (_candidate_relevance_score(c, query_terms=query_terms), i, c)
        for i, c in enumerate(candidates)
        if _has_handoff_source(c) or c.get("doi")
    ]
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    return scored[0][2] if scored[0][0] > 0 else None


def _seed_candidates(seed_response: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("upstream_papers", "downstream_papers", "same_route_papers", "related_surveys", "papers"):
        for paper in seed_response.get(key) or []:
            if isinstance(paper, dict):
                candidates.append(paper)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        identity = str(candidate.get("arxiv_id") or candidate.get("doi") or candidate.get("paper_id") or candidate.get("title") or "")
        if identity and identity not in seen:
            seen.add(identity)
            unique.append(candidate)
    return unique


def _select_handoff_candidate(candidates: list[dict[str, Any]], *, query: str = "") -> dict[str, Any] | None:
    query_terms = _query_terms(query)
    scored = [
        (_handoff_candidate_score(candidate, query_terms=query_terms), index, candidate)
        for index, candidate in enumerate(candidates)
        if _has_handoff_source(candidate)
    ]
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return scored[0][2] if scored[0][0] > 0 else None


def _has_handoff_source(candidate: dict[str, Any]) -> bool:
    return bool(_candidate_arxiv_id(candidate) or _candidate_arxiv_url(candidate) or candidate.get("pdf_url"))


def _candidate_relevance_score(candidate: dict[str, Any], *, query_terms: set[str] | None = None) -> int:
    """Score a candidate for query relevance, heavily penalizing surveys."""
    title = str(candidate.get("title") or "").lower()
    title_terms = _query_terms(title)
    score = 0

    # Query term overlap (core signal)
    if query_terms:
        overlap = query_terms & title_terms
        score += 5 * len(overlap)
        if not overlap:
            score -= 20

    # Required concept coverage for compound queries
    if query_terms:
        required = _required_concepts(query_terms)
        covered = sum(1 for concept_set in required if title_terms & concept_set)
        if len(required) >= 2 and covered < 2:
            score -= 15  # Penalize papers that miss most required concepts
        elif len(required) >= 2:
            score += 3 * covered  # Bonus for covering multiple concepts

    # Survey penalty (very strong — surveys are bad seeds)
    is_survey = _is_survey_like(title)
    if is_survey:
        score -= 25

    # Source readiness
    if candidate.get("can_enter_m2") is True or candidate.get("can_prepare_deep_read") is True:
        score += 3
    if _candidate_arxiv_id(candidate):
        score += 5
    elif candidate.get("pdf_url"):
        score += 3

    # Relation type
    relation_type = str(candidate.get("relation_type") or "").lower()
    relation_bonus = {"same_route": 5, "downstream": 4, "upstream": 1, "survey": -12}
    score += relation_bonus.get(relation_type, 0)

    # Positive/negative title terms
    positive_terms = [
        "method", "approach", "model", "framework", "architecture", "algorithm",
        "learning", "neural", "transformer", "imputation", "detection", "forecasting",
        "network", "encoder", "decoder", "attention", "diffusion", "graph",
        "time series", "anomaly", "prediction", "temporal", "spatial",
    ]
    negative_terms = [
        "survey", "review", "foundation model", "foundational model",
        "foundational models", "perspective", "role in", "benchmarking",
        "comparison", "comprehensive", "taxonomy",
    ]
    score += sum(1 for term in positive_terms if term in title)
    score -= 5 * sum(1 for term in negative_terms if term in title)
    return score


def _is_survey_like(title: str) -> bool:
    """Check if a title looks like a survey/review paper."""
    survey_indicators = ["survey", "review", "a survey", "comprehensive", "taxonomy", "overview"]
    return any(ind in title for ind in survey_indicators)


def _required_concepts(query_terms: set[str]) -> list[set[str]]:
    """Extract required concept groups from query terms for compound query coverage."""
    concepts: list[set[str]] = []
    # Graph/GNN concepts
    graph_terms = {"graph", "gnn", "neural", "network"} & query_terms
    if graph_terms:
        concepts.append(graph_terms)
    # Time series concepts
    ts_terms = {"time", "series", "temporal", "forecasting", "imputation"} & query_terms
    if ts_terms:
        concepts.append(ts_terms)
    # Anomaly/detection concepts
    anomaly_terms = {"anomaly", "detection", "outlier"} & query_terms
    if anomaly_terms:
        concepts.append(anomaly_terms)
    # Diffusion concepts
    diffusion_terms = {"diffusion", "score", "denoising"} & query_terms
    if diffusion_terms:
        concepts.append(diffusion_terms)
    # Transformer concepts
    transformer_terms = {"transformer", "attention"} & query_terms
    if transformer_terms:
        concepts.append(transformer_terms)
    # If no specific groups matched, treat each term as its own concept
    if not concepts:
        concepts = [{t} for t in query_terms]
    return concepts


def _handoff_candidate_score(candidate: dict[str, Any], *, query_terms: set[str] | None = None) -> int:
    """Score a handoff candidate (seed expansion papers)."""
    title = str(candidate.get("title") or "").lower()
    title_terms = _query_terms(title)
    relation_type = str(candidate.get("relation_type") or "").lower()
    score = 0
    if query_terms:
        overlap = query_terms & title_terms
        score += 5 * len(overlap)
        if not overlap:
            score -= 20
    # Survey penalty
    if _is_survey_like(title):
        score -= 25
    if candidate.get("can_enter_m2") is True or candidate.get("can_prepare_deep_read") is True:
        score += 3
    if _candidate_arxiv_id(candidate):
        score += 5
    elif candidate.get("pdf_url"):
        score += 3
    relation_bonus = {"same_route": 5, "downstream": 4, "upstream": 1, "survey": -12}
    score += relation_bonus.get(relation_type, 0)
    positive_terms = [
        "method", "approach", "model", "framework", "architecture", "algorithm",
        "learning", "neural", "transformer", "imputation", "detection", "forecasting",
        "network", "encoder", "decoder", "attention", "diffusion", "graph",
        "time series", "anomaly", "prediction", "temporal", "spatial",
    ]
    negative_terms = [
        "survey", "review", "foundation model", "foundational model",
        "foundational models", "perspective", "role in", "benchmarking",
        "comparison", "comprehensive", "taxonomy",
    ]
    score += sum(1 for term in positive_terms if term in title)
    score -= 5 * sum(1 for term in negative_terms if term in title)
    return score


def _query_terms(text: str) -> set[str]:
    stopwords = {
        "with",
        "from",
        "using",
        "based",
        "paper",
        "for",
        "the",
        "and",
        "of",
        "in",
        "on",
        "to",
        "a",
        "an",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 3 and token not in stopwords
    }


def _candidate_arxiv_id(candidate: dict[str, Any]) -> str:
    explicit = str(candidate.get("arxiv_id") or "").strip()
    if explicit and _is_supported_arxiv_id(explicit):
        return explicit
    for key in ("arxiv_url", "url", "landing_url", "paper_url", "pdf_url"):
        value = str(candidate.get(key) or "")
        match = re.search(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", value)
        if match:
            return match.group(1).removesuffix(".pdf")
    return ""


def _candidate_arxiv_url(candidate: dict[str, Any]) -> str:
    for key in ("arxiv_url", "url", "landing_url", "paper_url"):
        value = str(candidate.get(key) or "")
        if _candidate_arxiv_id({key: value}):
            return value
    return ""


def _candidate_sources(candidate: dict[str, Any]) -> list[str]:
    sources = candidate.get("sources")
    if isinstance(sources, list):
        return [str(source) for source in sources if source]
    source = str(candidate.get("source") or "")
    return [source] if source else []


def _selected_input_type(source_status: dict[str, Any]) -> str:
    source_type = str(source_status.get("source_type") or "")
    if source_type == "arxiv_source":
        return "arxiv_source"
    if source_type == "arxiv_pdf":
        return "arxiv_pdf"
    if source_type == "pdf_url":
        return "external_pdf"
    if source_type == "doi":
        return "metadata_only"
    return source_type or "unknown"


def _source_strategy(source_status: dict[str, Any]) -> str:
    explicit = str(source_status.get("source_strategy") or "")
    if explicit:
        return explicit
    selected = _selected_input_type(source_status)
    if selected == "arxiv_source":
        return "source_first"
    if selected == "arxiv_pdf":
        return "pdf_fallback"
    if selected == "external_pdf":
        return "pdf_direct"
    return "metadata_only"


def _formula_origin_summary(paper_workspace_status: dict[str, Any]) -> dict[str, Any]:
    summary = paper_workspace_status.get("formula_origin_summary")
    if isinstance(summary, dict):
        return summary
    origin = str(paper_workspace_status.get("formula_origin") or "")
    ocr = str(paper_workspace_status.get("formula_ocr_status") or "")
    result: dict[str, Any] = {}
    if origin:
        result["origins"] = origin
    if ocr:
        result["ocr_statuses"] = ocr
    if result:
        return result
    return {}


def _handoff_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": candidate.get("title") or "",
        "doi": candidate.get("doi") or "",
        "arxiv_id": _candidate_arxiv_id(candidate),
        "arxiv_url": _candidate_arxiv_url(candidate),
        "pdf_url": candidate.get("pdf_url") or "",
    }


def _is_supported_arxiv_id(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?", value.strip()))


def _warnings(response: dict[str, Any]) -> list[str]:
    raw = response.get("warnings") or []
    warnings: list[str] = []
    if isinstance(raw, list):
        for warning in raw:
            if isinstance(warning, str):
                warnings.append(warning)
            elif isinstance(warning, dict):
                code = str(warning.get("code") or "WARNING")
                message = str(warning.get("message") or warning.get("detail") or "")
                warnings.append(f"{code}: {message}".strip())
    return warnings


def _request_json(response: ResponseLike, stage: str) -> dict[str, Any]:
    payload = _safe_json(response)
    if response.status_code >= 400:
        raise RuntimeError(f"{stage} failed with HTTP {response.status_code}: {_safe_detail(payload)}")
    return payload


def _safe_json(response: ResponseLike) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_detail(payload: dict[str, Any]) -> str:
    detail = payload.get("detail") if isinstance(payload, dict) else ""
    if isinstance(detail, dict):
        return str({key: value for key, value in detail.items() if "key" not in key.lower()})
    return str(detail or payload)[:500]


def _fail(
    *,
    query: str,
    llm_enabled: bool,
    llm_mode_note: str,
    stage: str,
    message: str,
    warnings: list[str],
    selected_candidate: dict[str, Any] | None = None,
    seed_response: dict[str, Any] | None = None,
    source_metrics: Any = None,
    handoff_job_id: str = "",
    selected_input_type: str = "unknown",
    source_strategy: str = "metadata_only",
) -> dict[str, Any]:
    return {
        "query": query,
        "llm_enabled": llm_enabled,
        "llm_mode_note": llm_mode_note,
        "failed_stage": stage,
        "message": message,
        "selected_candidate_title": str((selected_candidate or {}).get("title") or ""),
        "selected_candidate_arxiv_id": str((selected_candidate or {}).get("arxiv_id") or ""),
        "selected_candidate_sources": _candidate_sources(selected_candidate or {}),
        "selected_input_type": selected_input_type,
        "source_strategy": source_strategy,
        "direction_source_metrics": _source_metrics_by_source(source_metrics),
        "seed_expansion_status": (seed_response or {}).get("seed_expansion_status") or (seed_response or {}).get("status") or "",
        "seed_expansion_group_counts": seed_group_counts(seed_response or {}),
        "handoff_job_id": handoff_job_id,
        "final_understanding_status": "",
        "cards_status_code": 0,
        "returned_card_components": [],
        "warnings": warnings,
        "final_verdict": "FAIL",
        "verdict_reasons": [message],
    }


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
