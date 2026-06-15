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
    direction_papers = _papers(direction_response)[:max(1, max_candidates)]
    direction_candidate = _select_arxiv_candidate(direction_papers)
    if not direction_candidate:
        return _fail(
            query=query,
            llm_enabled=llm_enabled,
            llm_mode_note=llm_mode_note,
            stage="direction_search",
            message="No arXiv candidate was returned by direction search.",
            warnings=warnings + _warnings(direction_response),
        )

    seed_response = _request_json(
        client.post("/api/v1/directions/seed_expansion", json={"seed": direction_candidate}),
        "seed expansion",
    )
    warnings.extend(_warnings(direction_response))
    warnings.extend(_warnings(seed_response))
    seed_candidates = _seed_candidates(seed_response)
    handoff_candidate = _select_handoff_candidate(seed_candidates[:max(1, max_candidates)])
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

    handoff_response = _request_json(
        client.post("/api/v1/directions/deep_read", json={"candidate": handoff_candidate}),
        "deep read handoff",
    )
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
        )

    status_response = _request_json(client.get(f"/api/v1/jobs/{job_id}/understanding_status"), "understanding status")
    understanding_status = status_response.get("understanding_status") or {}
    if not isinstance(understanding_status, dict):
        understanding_status = {}
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
        "selected_seed_handoff_title": str(handoff_candidate.get("title") or ""),
        "selected_seed_handoff_arxiv_id": _candidate_arxiv_id(handoff_candidate),
        "seed_expansion_status": seed_response.get("seed_expansion_status") or seed_response.get("status") or "",
        "seed_expansion_group_counts": seed_group_counts(seed_response),
        "handoff_job_id": job_id,
        "final_understanding_status": final_status,
        "blocking_reason": understanding_status.get("blocking_reason", ""),
        "cards_status_code": cards_status_code,
        "returned_card_components": returned_components,
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


def print_summary(result: dict[str, Any]) -> None:
    print("ResearchSensei main-chain smoke summary")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _papers(response: dict[str, Any]) -> list[dict[str, Any]]:
    papers = response.get("papers") or response.get("candidate_cards") or []
    return [paper for paper in papers if isinstance(paper, dict)]


def _select_arxiv_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for candidate in candidates:
        if candidate.get("arxiv_id"):
            return candidate
    for candidate in candidates:
        if _candidate_arxiv_id(candidate):
            return candidate
    return None


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


def _select_handoff_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for candidate in candidates:
        if _has_handoff_source(candidate) and (
            candidate.get("can_enter_m2") is True or candidate.get("can_prepare_deep_read") is True
        ):
            return candidate
    for candidate in candidates:
        if _has_handoff_source(candidate):
            return candidate
    return None


def _has_handoff_source(candidate: dict[str, Any]) -> bool:
    return bool(candidate.get("arxiv_id") or candidate.get("arxiv_url") or candidate.get("pdf_url"))


def _candidate_arxiv_id(candidate: dict[str, Any]) -> str:
    explicit = str(candidate.get("arxiv_id") or "").strip()
    if explicit:
        return explicit
    for key in ("arxiv_url", "url", "landing_url", "paper_url", "pdf_url"):
        value = str(candidate.get(key) or "")
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", value)
        if match:
            return match.group(1).removesuffix(".pdf")
    return ""


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
) -> dict[str, Any]:
    return {
        "query": query,
        "llm_enabled": llm_enabled,
        "llm_mode_note": llm_mode_note,
        "failed_stage": stage,
        "message": message,
        "selected_candidate_title": str((selected_candidate or {}).get("title") or ""),
        "selected_candidate_arxiv_id": str((selected_candidate or {}).get("arxiv_id") or ""),
        "seed_expansion_status": (seed_response or {}).get("seed_expansion_status") or (seed_response or {}).get("status") or "",
        "seed_expansion_group_counts": seed_group_counts(seed_response or {}),
        "handoff_job_id": "",
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
