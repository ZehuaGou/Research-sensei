from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchsensei.acquisition import ArxivAdapter, OpenAlexAdapter
from researchsensei.core.config import ConfigService, ModelProviderConfig
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.llm.client import LLMClient, parse_llm_json
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig
from researchsensei.schemas import JobStatus
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.workspace import WorkspaceStore


LIVE_QUERY = "time series anomaly detection transformer"
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
) -> dict[str, Any]:
    reason = config.live_skip_reason()
    if reason:
        return _failed_result("m1_live_search", reason, skipped=True)

    candidates = []
    source_log: list[dict[str, Any]] = []
    max_results = max(1, min(config.max_live_cases, 10))
    for source_name, adapter in (
        ("arxiv", ArxivAdapter()),
        ("openalex", OpenAlexAdapter()),
    ):
        try:
            results = adapter.search(query, max_results=max_results)
            candidates.extend(results)
            source_log.append({"source": source_name, "status": "passed", "count": len(results)})
        except Exception as exc:
            source_log.append({
                "source": source_name,
                "status": "failed",
                "reason": f"{type(exc).__name__}: {str(exc)[:200]}",
            })

    limited_candidates = candidates[: config.max_live_cases]
    resolver = PaperSourceResolver(network_enabled=False)
    source_resolution = resolver.resolve_many(query=query, candidates=limited_candidates)
    counts = _source_resolution_counts(source_resolution.items)
    status = "passed" if limited_candidates else "failed"
    return {
        "name": "m1_live_search",
        "status": status,
        "real_network": True,
        "query": query,
        "candidate_count": len(limited_candidates),
        "source_log": source_log,
        "source_resolution": counts,
        "sample_candidates": [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "source": paper.source,
                "arxiv_id": paper.arxiv_id,
                "doi": paper.doi,
                "pdf_url_present": bool(paper.pdf_url),
            }
            for paper in limited_candidates
        ],
        "semantic_scholar_status": "not_implemented",
        "crossref_status": "not_implemented",
        "failure_reason": "" if limited_candidates else "No candidates returned from live arXiv/OpenAlex search.",
    }


def run_m2_real_llm_smoke(config: LiveEvalConfig, *, work_dir: str | Path) -> dict[str, Any]:
    reason = config.llm_skip_reason()
    if reason:
        return _failed_result("m2_real_llm_smoke", reason, skipped=True)

    work_root = Path(work_dir)
    work_root.mkdir(parents=True, exist_ok=True)
    source = _sample_paper_path(work_root)
    llm_client = build_live_llm_client(config)
    workspace = WorkspaceStore(work_root / "workspace")
    jobs = JobStore(work_root / "jobs.sqlite")
    job_id = f"live-llm-smoke-{int(time.time() * 1000)}"
    started = time.perf_counter()
    try:
        job = SinglePaperIngestionRunner(
            workspace=workspace,
            jobs=jobs,
            llm_client=llm_client,
        ).run(source, job_id=job_id)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if job.status != JobStatus.SUCCEEDED:
            return _failed_result(
                "m2_real_llm_smoke",
                job.error or "SinglePaperIngestionRunner did not succeed.",
                extra={"job_status": job.status.value, "token_usage": llm_client.usage.as_dict()},
            )
        return _summarize_m2_job(job, llm_client, latency_ms)
    except Exception as exc:
        return _failed_result(
            "m2_real_llm_smoke",
            f"{type(exc).__name__}: {str(exc)[:300]}",
            extra={"token_usage": llm_client.usage.as_dict(), "model": llm_client.usage.model},
        )


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
        "schema_version": "v1",
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
        "m1_live": run_m1_live_search(actual_config),
        "m2_real_llm": {},
    }
    report["m2_real_llm"] = run_m2_real_llm_smoke(actual_config, work_dir=work_root)
    report_path = report_dir / "live_eval_report.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(_redact_report(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _summarize_m2_job(job, llm_client: MeteredLLMClient, latency_ms: int) -> dict[str, Any]:
    run_dir = Path(job.run_dir)
    artifacts = {artifact.artifact_type: Path(artifact.path) for artifact in job.artifacts}
    quality_report_path = artifacts.get("quality_report")
    understanding_status_path = artifacts.get("understanding_status")
    paper_card = _load_json(artifacts.get("paper_card"))
    evidence_index = _load_json(artifacts.get("evidence_index")) or {}
    understanding_status = _load_json(understanding_status_path) or {}
    quality_report = _load_json(quality_report_path) or {}
    common_extra = {
        "real_llm": True,
        "model": llm_client.usage.model,
        "token_usage": llm_client.usage.as_dict(),
        "estimated_cost_usd": round(llm_client.usage.estimated_cost_usd, 6),
        "artifacts": {
            "run_dir": str(run_dir),
            "quality_report": str(quality_report_path) if quality_report_path else "",
            "understanding_status": str(understanding_status_path) if understanding_status_path else "",
            "paper_card": str(artifacts.get("paper_card", "")),
        },
        "understanding_status": understanding_status.get("status", ""),
        "allowed_for_user_display": bool(understanding_status.get("allowed_for_user_display", False)),
    }
    if llm_client.usage.call_count == 0:
        return _failed_result(
            "m2_real_llm_smoke",
            "Pipeline completed without making a real LLM call.",
            extra=common_extra,
        )

    evidence_refs = _collect_card_evidence_refs(paper_card)
    traceable_refs = _evidence_refs(evidence_index)
    evidence_ref_traceable = bool(evidence_refs) and all(ref in traceable_refs for ref in evidence_refs)

    return {
        "name": "m2_real_llm_smoke",
        "status": "passed",
        "real_llm": True,
        "model": llm_client.usage.model,
        "prompt_version": "paper_card_v2/formula_card_v2/teaching_card_v2",
        "schema_version": "v1",
        "latency_ms": latency_ms,
        "token_usage": llm_client.usage.as_dict(),
        "estimated_cost_usd": round(llm_client.usage.estimated_cost_usd, 6),
        "artifacts": common_extra["artifacts"],
        "has_evidence_ref": bool(evidence_refs),
        "evidence_ref_traceable": evidence_ref_traceable,
        "allowed_for_user_display": bool(understanding_status.get("allowed_for_user_display", False)),
        "understanding_status": understanding_status.get("status", ""),
        "quality_findings": len(quality_report.get("findings", [])),
        "failure_reason": "",
    }


def _source_resolution_counts(items) -> dict[str, int]:
    counts = {"total": len(items), "resolved": 0, "partial": 0, "failed": 0, "not_found": 0}
    for item in items:
        status = item.status.value
        if status == "RESOLVED":
            counts["resolved"] += 1
        elif status == "PARTIAL":
            counts["partial"] += 1
        elif status == "FAILED":
            counts["failed"] += 1
        elif status == "NOT_FOUND":
            counts["not_found"] += 1
    return counts


def _sample_paper_path(work_root: Path) -> Path:
    sample = work_root / "synthetic_live_paper.md"
    sample.write_text(
        """# Synthetic GraphAD Paper

## Abstract
We propose a graph model for anomaly detection in multivariate time series.

## Method
We propose a method that builds a sensor graph and uses reconstruction error.
The loss is L = L_rec + lambda L_graph.

## Experiments
The method is evaluated on a small synthetic benchmark and reports F1 score.

## Limitations
The method assumes a fixed graph structure.
""",
        encoding="utf-8",
    )
    return sample


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_card_evidence_refs(paper_card: dict[str, Any] | None) -> list[str]:
    if not paper_card:
        return []
    refs = list(paper_card.get("evidence_refs", []))
    for field in ("problem", "core_idea", "method_overview", "experiment_summary", "limitations"):
        value = paper_card.get(field)
        if isinstance(value, dict) and value.get("evidence_ref"):
            refs.append(value["evidence_ref"])
    return sorted({ref for ref in refs if ref})


def _evidence_refs(evidence_index: dict[str, Any]) -> set[str]:
    return {
        claim.get("evidence_ref", "")
        for claim in evidence_index.get("claims", [])
        if claim.get("evidence_ref")
    }


def _failed_result(
    name: str,
    reason: str,
    *,
    skipped: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
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
    for secret_name in ("DEEPSEEK_API_KEY", "MIMO_API_KEY", "OPENAI_COMPATIBLE_API_KEY"):
        secret = os.getenv(secret_name, "")
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def run_async(coro):
    return asyncio.run(coro)
