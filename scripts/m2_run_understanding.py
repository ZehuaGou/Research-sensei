"""Run M2 understanding from an M1 artifact bundle."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.core.config import ConfigService, ModelProviderConfig  # noqa: E402
from researchsensei.llm.client import LLMClient, parse_llm_json  # noqa: E402
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig  # noqa: E402
from researchsensei.m2.artifact_reader import M1ArtifactReader  # noqa: E402
from researchsensei.m2.full_pipeline import run_m2_full_pipeline  # noqa: E402
from researchsensei.m2.runner import run_m2_understanding  # noqa: E402


class M2LLMUsage:
    def __init__(self, model: str = "") -> None:
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.latencies_ms: list[int] = []

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "latencies_ms": self.latencies_ms,
        }


class MeteredM2LLMClient:
    """Small wrapper matching LLMClient.chat_json while recording live-call metadata."""

    def __init__(self, provider: ModelProviderConfig, config: LLMConfig) -> None:
        self.provider = provider
        self.client = LLMClient(provider, config=config)
        self.config = config
        self.usage = M2LLMUsage(model=provider.model)

    async def chat(self, messages: list[ChatMessage], *, config: LLMConfig | None = None) -> ChatResponse:
        cfg = config or self.config
        started = time.perf_counter()
        response = await self.client.chat(messages, config=cfg)
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._record(response, messages, latency_ms)
        return response

    async def chat_json(self, messages: list[ChatMessage], *, config: LLMConfig | None = None) -> dict:
        cfg = config or self.config.model_copy(update={"json_mode": True, "temperature": 0.2})
        response = await self.chat(messages, config=cfg)
        return parse_llm_json(response.content)

    def _record(self, response: ChatResponse, messages: list[ChatMessage], latency_ms: int) -> None:
        prompt_tokens = response.usage_prompt_tokens or _estimate_tokens("\n".join(m.content for m in messages))
        completion_tokens = response.usage_completion_tokens or _estimate_tokens(response.content)
        total_tokens = response.usage_total_tokens or (prompt_tokens + completion_tokens)
        self.usage.model = response.model or self.usage.model
        self.usage.prompt_tokens += prompt_tokens
        self.usage.completion_tokens += completion_tokens
        self.usage.total_tokens += total_tokens
        self.usage.call_count += 1
        self.usage.latencies_ms.append(latency_ms)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M2 understanding from M1 canonical artifacts.")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="M1 artifact directory containing canonical_paper.md, formula_slots.json, and related files.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Output directory. Defaults to reports/m2_understanding_<paper_id> or reports/m2_full_<paper_id>.",
    )
    parser.add_argument(
        "--mode",
        choices=["diagnostic", "full"],
        default="diagnostic",
        help="diagnostic keeps the existing rule-based M2 report; full runs the M2.1-M2.5 artifact chain.",
    )
    parser.add_argument("--enable-llm", action="store_true", help="Use the configured real LLM for full mode.")
    parser.add_argument("--provider", default="", help="Provider name from config/local.toml, e.g. mimo.")
    parser.add_argument("--llm-max-tokens", type=int, default=2400, help="Max output tokens per LLM call.")
    parser.add_argument("--llm-timeout", type=float, default=0.0, help="Override provider timeout seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    bundle = M1ArtifactReader(input_dir).load()
    paper_id = str(bundle.front_matter.get("paper_id") or bundle.paper_metadata.get("paper_id") or input_dir.name)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    elif args.mode == "full":
        output_dir = ROOT / "reports" / f"m2_full_{paper_id}"
    else:
        output_dir = ROOT / "reports" / f"m2_understanding_{paper_id}"

    if args.mode == "diagnostic":
        result = run_m2_understanding(input_dir=input_dir, output_dir=output_dir)
        print(f"M2 diagnostic understanding written to: {output_dir}")
        print(f"Formula count: {result.run_summary['formula_count']}")
        print(f"Skipped formulas: {result.run_summary['skipped_formula_count']}")
        print(f"M1 artifacts modified: {result.run_summary['m1_artifacts_modified']}")
        return 0

    llm_client = None
    llm_metadata = {"provider": "none", "model": "", "call_count": 0}
    if args.enable_llm:
        config = ConfigService().load()
        provider_name = args.provider or config.active_provider
        if provider_name not in config.providers:
            print(f"ERROR: unknown provider '{provider_name}'", file=sys.stderr)
            return 2
        provider = config.providers[provider_name]
        missing = provider.missing_api_key_message()
        import os
        if not os.getenv(provider.api_key_env, ""):
            print(f"ERROR: {missing}", file=sys.stderr)
            return 2
        llm_config = LLMConfig(
            temperature=0.2,
            max_tokens=args.llm_max_tokens,
            json_mode=True,
            timeout=args.llm_timeout or float(provider.timeout_seconds or 60),
            max_retries=0,
        )
        llm_client = MeteredM2LLMClient(provider, llm_config)
        llm_metadata = {"provider": provider.name, "model": provider.model}

    result = run_m2_full_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        llm_client=llm_client,
        llm_metadata=llm_metadata,
    )
    print(f"M2 full pipeline written to: {output_dir}")
    print(f"Status: {result.status.status}")
    print(f"Blocking reason: {result.status.blocking_reason or 'none'}")
    print(f"LLM calls: {getattr(llm_client, 'usage', M2LLMUsage()).call_count if llm_client else 0}")
    return 0 if result.status.status in {"SUCCESS", "DEGRADED_STRUCTURAL", "BASELINE_ONLY"} else 2


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


if __name__ == "__main__":
    raise SystemExit(main())
