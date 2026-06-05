from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchsensei.core.config import ConfigService, ModelProviderConfig
from researchsensei.direction import DirectionRunner
from researchsensei.llm.client import LLMClient, parse_llm_json
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig
from researchsensei.query import QueryPlanner
from researchsensei.relevance_judge import RelevanceJudge
from researchsensei.schemas import PaperSourceStatus
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.verification import CandidateVerifier
from researchsensei.workspace import WorkspaceStore

LIVE_QUERY = "时间序列异常检测 transformer 方法"
DEFAULT_REPORT_DIR = Path("reports/live_eval")


class LiveEvalError(RuntimeError):
    """Raised when live eval setup or execution fails."""


class LiveEvalBudgetExceeded(LiveEvalError):
    """Raised when a live LLM request would exceed configured limits."""


@dataclass(frozen=True)
class LiveEvalConfig:
    run_live_tests: bool
    run_llm_tests: bool
    live_eval_enabled: bool
    max_live_cases: int
    max_llm_cost_usd: float
    max_llm_tokens: int
    report_dir: Path
    provider: ModelProviderConfig
    prompt_cost_per_1k_usd: float = 0.0
    completion_cost_per_1k_usd: float = 0.0
    llm_max_output_tokens: int = 1200
    llm_timeout_seconds: float = 60.0
    active_provider_name: str = ""

    @classmethod
    def from_env(
        cls,
        *,
        report_dir: str | Path | None = None,
        load_dotenv: bool = True,
    ) -> "LiveEvalConfig":
        env_path = ".env" if load_dotenv else "__researchsensei_missing_env__"
        app_config = ConfigService(env_path=env_path).load()
        provider = app_config.active_model_provider()
        override_provider = os.getenv("RESEARCHSENSEI_LIVE_PROVIDER", "").strip()
        if override_provider:
            if override_provider not in app_config.providers:
                raise LiveEvalError(f"Unknown RESEARCHSENSEI_LIVE_PROVIDER: {override_provider}")
            provider = app_config.providers[override_provider]

        max_llm_tokens = _env_int("RESEARCHSENSEI_MAX_LLM_TOKENS", 20_000, minimum=1)
        default_output_tokens = max(256, min(1200, max_llm_tokens // 6))
        return cls(
            run_live_tests=_env_flag("RUN_LIVE_TESTS"),
            run_llm_tests=_env_flag("RUN_LLM_TESTS"),
            live_eval_enabled=_env_flag("RESEARCHSENSEI_LIVE_EVAL"),
            max_live_cases=_env_int("RESEARCHSENSEI_MAX_LIVE_CASES", 3, minimum=1),
            max_llm_cost_usd=_env_float("RESEARCHSENSEI_MAX_LLM_COST_USD", 1.0, minimum=0.0),
            max_llm_tokens=max_llm_tokens,
            report_dir=Path(report_dir or DEFAULT_REPORT_DIR),
            provider=provider,
            prompt_cost_per_1k_usd=_env_float("RESEARCHSENSEI_LLM_PROMPT_COST_PER_1K_USD", 0.0, minimum=0.0),
            completion_cost_per_1k_usd=_env_float("RESEARCHSENSEI_LLM_COMPLETION_COST_PER_1K_USD", 0.0, minimum=0.0),
            llm_max_output_tokens=_env_int("RESEARCHSENSEI_LLM_MAX_OUTPUT_TOKENS", default_output_tokens, minimum=1),
            llm_timeout_seconds=float(provider.timeout_seconds or 60),
            active_provider_name=provider.name,
        )

    def live_skip_reason(self) -> str:
        missing: list[str] = []
        if not self.run_live_tests:
            missing.append("RUN_LIVE_TESTS=1")
        if not self.live_eval_enabled:
            missing.append("RESEARCHSENSEI_LIVE_EVAL=1")
        if missing:
            return " and ".join(missing) + " are required"
        return ""

    def llm_skip_reason(self) -> str:
        missing: list[str] = []
        if not self.run_llm_tests:
            missing.append("RUN_LLM_TESTS=1")
        if not self.live_eval_enabled:
            missing.append("RESEARCHSENSEI_LIVE_EVAL=1")
        if missing:
            return " and ".join(missing) + " are required"
        if not os.getenv(self.provider.api_key_env, ""):
            return f"Missing credential. Set {self.provider.api_key_env}."
        return ""


@dataclass
class LLMUsageMeter:
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    call_count: int = 0
    latencies_ms: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "call_count": self.call_count,
            "latencies_ms": self.latencies_ms,
        }


class MeteredLLMClient:
    """OpenAI-compatible LLM client wrapper with live-eval budget accounting."""

    def __init__(self, client: LLMClient, config: LiveEvalConfig) -> None:
        self.client = client
        self.config = config
        self.usage = LLMUsageMeter(model=config.provider.model)

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> ChatResponse:
        cfg = config or self.client.config
        self._check_preflight_budget(messages, cfg)
        started = time.perf_counter()
        response = await self.client.chat(messages, config=cfg)
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._record_response(response, messages, latency_ms)
        self._check_post_response_budget()
        return response

    async def chat_json(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> dict:
        cfg = config or self.client.config.model_copy(update={"json_mode": True, "temperature": 0.2})
        response = await self.chat(messages, config=cfg)
        return parse_llm_json(response.content)

    def _check_preflight_budget(self, messages: list[ChatMessage], config: LLMConfig) -> None:
        estimated_prompt = _estimate_tokens("\n".join(message.content for message in messages))
        projected = self.usage.total_tokens + estimated_prompt + config.max_tokens
        if projected > self.config.max_llm_tokens:
            raise LiveEvalBudgetExceeded(
                f"LLM token budget would be exceeded: projected={projected}, "
                f"limit={self.config.max_llm_tokens}"
            )

    def _record_response(self, response: ChatResponse, messages: list[ChatMessage], latency_ms: int) -> None:
        prompt_tokens = response.usage_prompt_tokens or _estimate_tokens("\n".join(m.content for m in messages))
        completion_tokens = response.usage_completion_tokens or _estimate_tokens(response.content)
        total_tokens = response.usage_total_tokens or (prompt_tokens + completion_tokens)
        self.usage.model = response.model or self.usage.model
        self.usage.prompt_tokens += prompt_tokens
        self.usage.completion_tokens += completion_tokens
        self.usage.total_tokens += total_tokens
        self.usage.call_count += 1
        self.usage.latencies_ms.append(latency_ms)
        self.usage.estimated_cost_usd += (
            prompt_tokens / 1000 * self.config.prompt_cost_per_1k_usd
            + completion_tokens / 1000 * self.config.completion_cost_per_1k_usd
        )

    def _check_post_response_budget(self) -> None:
        if self.usage.total_tokens > self.config.max_llm_tokens:
            raise LiveEvalBudgetExceeded(
                f"LLM token budget exceeded: used={self.usage.total_tokens}, "
                f"limit={self.config.max_llm_tokens}"
            )
        if self.usage.estimated_cost_usd > self.config.max_llm_cost_usd:
            raise LiveEvalBudgetExceeded(
                f"LLM cost budget exceeded: estimated={self.usage.estimated_cost_usd:.4f}, "
                f"limit={self.config.max_llm_cost_usd:.4f}"
            )


def build_live_llm_client(config: LiveEvalConfig) -> MeteredLLMClient:
    reason = config.llm_skip_reason()
    if reason:
        raise LiveEvalError(reason)
    llm_config = LLMConfig(
        temperature=0.2,
        max_tokens=min(config.llm_max_output_tokens, config.max_llm_tokens),
        json_mode=True,
        timeout=config.llm_timeout_seconds,
        max_retries=0,
    )
    return MeteredLLMClient(LLMClient(config.provider, config=llm_config), config)


def run_m1_live_search(
    config: LiveEvalConfig,
    *,
    query: str = LIVE_QUERY,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    live_reason = config.live_skip_reason()
    if live_reason:
        return _failed_result("m1_live_search", live_reason, skipped=True)
    llm_reason = config.llm_skip_reason()
    if llm_reason:
        return _failed_result("m1_live_search", llm_reason)

    work_root = Path(work_dir or config.report_dir / "work" / "m1")
    workspace = WorkspaceStore(work_root / "workspace")
    llm_client = build_live_llm_client(config)
    source_resolver = PaperSourceResolver(
        network_enabled=True,
        download_dir=work_root / "downloads",
        timeout_seconds=12.0,
        max_download_bytes=80 * 1024 * 1024,
    )
    verifier = CandidateVerifier(
        s2_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
    )
    relevance_judge = RelevanceJudge(
        llm_client=llm_client,
        enabled=True,
    )
    runner = DirectionRunner(
        workspace=workspace,
        query_planner=QueryPlanner(llm_client=llm_client),
        source_resolver=source_resolver,
        verifier=verifier,
        relevance_judge=relevance_judge,
        max_results_per_source=max(1, min(config.max_live_cases, 5)),
    )
    started = time.perf_counter()
    try:
        bundle = run_async(runner.run(query, direction_id="m1-live"))
    except Exception as exc:
        return _failed_result(
            "m1_live_search",
            f"{type(exc).__name__}: {str(exc)[:300]}",
            extra={
                "real_llm_query_planning": llm_client.usage.call_count > 0,
                "token_usage": llm_client.usage.as_dict(),
                "query": query,
            },
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    source_metrics = bundle.candidate_pool.source_metrics
    counts_by_source = {str(metric["source"]): int(metric.get("count", 0)) for metric in source_metrics}
    sources_success = [str(metric["source"]) for metric in source_metrics if metric.get("success")]
    pdf_url_count = sum(1 for paper in bundle.filtered_candidates.items if paper.pdf_url or paper.pdf_available)
    pdf_download_success_count = sum(
        1 for item in bundle.source_resolution.items if item.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
    )
    a_read_items = [item for item in bundle.reading_plan.items if item.priority == "A_READ"]
    a_read_can_enter_m2 = [item.paper.paper_id for item in a_read_items if item.can_enter_m2 and item.paper.can_enter_m2]
    downloaded = [item for item in bundle.source_resolution.items if item.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED]

    # Build a_read paper_ids for downloaded_sources check
    a_read_paper_ids = {item.paper.paper_id for item in a_read_items}

    # Verification and relevance summary
    verification_summary = bundle.verification_summary
    relevance_summary = bundle.relevance_summary

    # M1 live status: passed / degraded_passed / failed
    # Strict check: every A_READ must satisfy ALL gate conditions
    failure_reasons: list[str] = []
    if llm_client.usage.call_count <= 0:
        failure_reasons.append("No real LLM query-planning call was made.")
    if not bundle.query_plan.english_query:
        failure_reasons.append("Query plan did not produce english_query.")
    if not sources_success:
        failure_reasons.append("No mature search source returned candidates.")
    if bundle.candidate_pool.retrieved_count <= 0:
        failure_reasons.append("No candidate papers were retrieved.")
    if pdf_download_success_count <= 0:
        failure_reasons.append("No real PDF was downloaded and validated.")
    if not a_read_items:
        failure_reasons.append("No A_READ item was selected.")

    # Check each A_READ strictly
    from researchsensei.schemas import VerificationStatus as VS
    a_read_gate_failures: list[str] = []
    for item in a_read_items:
        p = item.paper
        sr_meta = p.raw_source_metadata.get("source_resolution", {})
        pdf_meta = sr_meta.get("pdf_metadata_check", "") if isinstance(sr_meta, dict) else ""
        pdf_title = sr_meta.get("pdf_title_match", "") if isinstance(sr_meta, dict) else ""

        reasons = []
        if p.verification_status != VS.VERIFIED:
            reasons.append(f"verification_status={p.verification_status.value}")
        if p.llm_relevance_score < 0.65:
            reasons.append(f"llm_relevance_score={p.llm_relevance_score}")
        if p.llm_relevance_label not in ("HIGH", "MEDIUM"):
            reasons.append(f"llm_relevance_label={p.llm_relevance_label}")
        if not p.should_a_read:
            reasons.append("should_a_read=false")
        if not p.pdf_downloaded:
            reasons.append("pdf_downloaded=false")
        if not item.can_enter_m2:
            reasons.append("can_enter_m2=false")
        if pdf_meta != "passed":
            reasons.append(f"pdf_metadata_check={pdf_meta}")
        if pdf_title != "match":
            reasons.append(f"pdf_title_match={pdf_title}")
        if not _confidence_at_least(p.source_confidence, "medium"):
            reasons.append(f"source_confidence={p.source_confidence}")
        if not _confidence_at_least(p.metadata_confidence, "medium"):
            reasons.append(f"metadata_confidence={p.metadata_confidence}")

        if reasons:
            a_read_gate_failures.append(f"'{p.title[:50]}': {'; '.join(reasons)}")

    if a_read_gate_failures:
        failure_reasons.append(f"A_READ gate failures: {a_read_gate_failures[0]}")

    # Determine M1 status per M1 doc: passed / degraded_passed / failed
    sources_success_count = len(sources_success)
    all_a_read_valid = a_read_items and not a_read_gate_failures

    if failure_reasons:
        status = "failed"
    elif sources_success_count >= 3 and pdf_download_success_count >= 1 and all_a_read_valid:
        status = "passed"
    elif sources_success_count == 2 and pdf_download_success_count >= 1 and all_a_read_valid:
        status = "degraded_passed"
    else:
        status = "failed"

    def _a_read_sample(item):
        p = item.paper
        sr_meta = p.raw_source_metadata.get("source_resolution", {})
        return {
            "paper_id": p.paper_id,
            "title": p.title,
            "sources": p.sources,
            "role": item.role,
            "can_enter_m2": item.can_enter_m2 and p.can_enter_m2,
            "pdf_downloaded": p.pdf_downloaded,
            "score": item.scoring_breakdown.weighted_total,
            "verification_status": p.verification_status.value,
            "verification_method": p.verification_method,
            "verification_reason": p.verification_reason,
            "verification_confidence": p.verification_confidence,
            "rule_relevance_score": p.rule_relevance_score,
            "llm_relevance_score": p.llm_relevance_score,
            "llm_relevance_label": p.llm_relevance_label,
            "should_download": p.should_download,
            "should_a_read": p.should_a_read,
            "matched_concepts": p.matched_concepts,
            "missing_concepts": p.missing_concepts,
            "relevance_reason": p.relevance_reason,
            "pdf_file_size": sr_meta.get("file_size", 0) if isinstance(sr_meta, dict) else 0,
            "pdf_sha256": sr_meta.get("sha256", "") if isinstance(sr_meta, dict) else "",
            "pdf_metadata_check": sr_meta.get("pdf_metadata_check", "") if isinstance(sr_meta, dict) else "",
            "pdf_title_match": sr_meta.get("pdf_title_match", "") if isinstance(sr_meta, dict) else "",
            "selection_reason": item.selection_reason,
            "risk_note": item.risk_note,
        }

    sample_a_read = [_a_read_sample(item) for item in a_read_items[: config.max_live_cases]]

    run_dir = workspace.root / "runs" / "m1-live"
    return {
        "name": "m1_live_search",
        "status": status,
        "failure_reason": "; ".join(failure_reasons),
        "real_network": True,
        "real_llm_query_planning": llm_client.usage.call_count > 0,
        "query": query,
        "english_query": bundle.query_plan.english_query,
        "query_variants": bundle.query_plan.query_variants,
        "sources_attempted": [str(metric["source"]) for metric in source_metrics],
        "sources_success": sources_success,
        "source_metrics": source_metrics,
        "arxiv_count": counts_by_source.get("arxiv", 0),
        "openalex_count": counts_by_source.get("openalex", 0),
        "semantic_scholar_count": counts_by_source.get("semantic_scholar", 0),
        "crossref_count": counts_by_source.get("crossref", 0),
        "candidate_count": bundle.candidate_pool.retrieved_count,
        "dedup_before": bundle.candidate_pool.retrieved_count,
        "dedup_after": bundle.filtered_candidates.deduplicated_count,
        "pdf_url_count": pdf_url_count,
        "pdf_download_success_count": pdf_download_success_count,
        "downloaded_sources": [
            {
                "paper_id": item.paper_id,
                "title": item.title,
                "source_url": item.source_url,
                "final_url": item.final_url,
                "content_type": item.content_type,
                "file_size": item.file_size,
                "sha256": item.sha256,
                "local_path": item.local_path,
                "pdf_metadata_check": item.pdf_metadata_check,
                "pdf_title_match": item.pdf_title_match,
                "pdf_metadata_warning": item.pdf_metadata_warning,
                "whether_a_read": item.paper_id in a_read_paper_ids,
                "if_not_a_read_reason": "" if item.paper_id in a_read_paper_ids else _not_a_read_reason(item, bundle),
            }
            for item in downloaded[: config.max_live_cases]
        ],
        "verified_candidate_count": verification_summary.get("verified_candidate_count", 0),
        "unverified_candidate_count": verification_summary.get("unverified_candidate_count", 0),
        "verify_pending_count": verification_summary.get("verify_pending_count", 0),
        "llm_judged_candidate_count": relevance_summary.get("llm_judged_candidate_count", 0),
        "relevance_filtered_count": relevance_summary.get("relevance_filtered_count", 0),
        "a_read_count": len(a_read_items),
        "a_read_can_enter_m2_count": len(a_read_can_enter_m2),
        "reading_plan_status": bundle.reading_plan.status,
        "sample_a_read": sample_a_read,
        "warnings": bundle.warnings,
        "latency_ms": latency_ms,
        "token_usage": llm_client.usage.as_dict(),
        "estimated_cost_usd": round(llm_client.usage.estimated_cost_usd, 6),
        "artifacts": {
            "run_dir": str(run_dir),
            "query_plan": str(run_dir / "query_plan.json"),
            "candidate_pool": str(run_dir / "candidate_pool.json"),
            "source_resolution": str(run_dir / "source_resolution.json"),
            "filtered_candidates": str(run_dir / "filtered_candidates.json"),
            "reading_plan": str(run_dir / "reading_plan.json"),
        },
    }


def run_full_live_eval(
    *,
    config: LiveEvalConfig | None = None,
    work_dir: str | Path | None = None,
) -> dict[str, Any]:
    actual_config = config or LiveEvalConfig.from_env()
    report_dir = actual_config.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    work_root = Path(work_dir or report_dir / "work")
    report: dict[str, Any] = {
        "schema_version": "v2-m1-real",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "live_eval": {
            "enabled": actual_config.live_eval_enabled,
            "run_live_tests": actual_config.run_live_tests,
            "run_llm_tests": actual_config.run_llm_tests,
        },
        "limits": {
            "max_live_cases": actual_config.max_live_cases,
            "max_llm_cost_usd": actual_config.max_llm_cost_usd,
            "max_llm_tokens": actual_config.max_llm_tokens,
        },
        "model": {
            "provider": actual_config.active_provider_name,
            "model": actual_config.provider.model,
            "base_url": actual_config.provider.base_url,
            "credential_env": actual_config.provider.api_key_env,
        },
        "m1_live": run_m1_live_search(actual_config, work_dir=work_root / "m1"),
    }
    report_path = report_dir / "live_eval_report.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(_redact_report(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _failed_result(
    name: str,
    reason: str,
    *,
    skipped: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "status": "skipped" if skipped else "failed",
        "failure_reason": reason,
    }
    if extra:
        result.update(extra)
    return result


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _redact_report(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_report(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_report(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_like_text(value)
    return value


def _redact_secret_like_text(value: str) -> str:
    redacted = value
    for secret_name in ("DEEPSEEK_API_KEY", "MIMO_API_KEY", "OPENAI_COMPATIBLE_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"):
        secret = os.getenv(secret_name, "")
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def run_async(coro):
    return asyncio.run(coro)


_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _confidence_at_least(value: str, minimum: str) -> bool:
    return _CONFIDENCE_ORDER.get(value, 0) >= _CONFIDENCE_ORDER.get(minimum, 0)


def _not_a_read_reason(item, bundle) -> str:
    """Explain why a downloaded PDF did not enter A_READ."""
    paper_id = item.paper_id
    # Find in reading_plan
    for rp_item in bundle.reading_plan.items:
        if rp_item.paper.paper_id == paper_id:
            p = rp_item.paper
            sr_meta = p.raw_source_metadata.get("source_resolution", {})
            pdf_meta = sr_meta.get("pdf_metadata_check", "") if isinstance(sr_meta, dict) else ""
            pdf_title = sr_meta.get("pdf_title_match", "") if isinstance(sr_meta, dict) else ""
            reasons = []
            if p.verification_status.value != "verified":
                reasons.append(f"verification={p.verification_status.value}")
            if p.llm_relevance_score < 0.65:
                reasons.append(f"llm_relevance={p.llm_relevance_score}")
            if not p.should_a_read:
                reasons.append("should_a_read=false")
            if pdf_meta != "passed":
                reasons.append(f"pdf_meta={pdf_meta}")
            if pdf_title != "match":
                reasons.append(f"pdf_title={pdf_title}")
            if rp_item.priority != "A_READ":
                reasons.append(f"priority={rp_item.priority}")
            return "; ".join(reasons) if reasons else "unknown"
    return "not_in_reading_plan"
