from __future__ import annotations

import logging

from researchsensei.llm.client import LLMClient, MockLLMClient, parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.schemas import QueryPlan
from researchsensei.schemas.enums import SearchIntent

logger = logging.getLogger(__name__)


class QueryPlanningError(RuntimeError):
    """Raised when M1 cannot produce a real LLM query plan."""


class QueryPlanner:
    """Generates structured query plans from user direction input."""

    def __init__(self, llm_client: LLMClient | MockLLMClient | None = None) -> None:
        self.llm = llm_client

    async def plan(self, user_query: str) -> QueryPlan:
        """Generate a query plan from user input.

        M1 must not silently fall back to heuristic query planning. A missing or
        invalid LLM plan is a real blocker because Chinese research directions
        often need precise English academic query terms.
        """
        if self.llm is None:
            raise QueryPlanningError("M1_QUERY_PLANNING_REQUIRES_REAL_LLM")

        try:
            return await self._plan_with_llm(user_query)
        except Exception as exc:
            logger.warning("LLM query planning failed: %s", exc)
            raise QueryPlanningError(f"M1_QUERY_PLANNING_FAILED: {type(exc).__name__}: {exc}") from exc

    async def _plan_with_llm(self, user_query: str) -> QueryPlan:
        prompt_builder = PromptBuilder()
        messages = prompt_builder.build_simple(
            system=(
                "You are ResearchSensei's research-query planning engine.\n"
                "Convert the user's research direction into precise English academic search terms.\n"
                "Preserve every core constraint in the user's query: data type, task, method family, and application domain.\n"
                "Do not broaden the query by dropping task/domain terms. If the user writes Chinese, translate the full phrase.\n"
                "Return strict JSON only. Do not include markdown."
            ),
            user=f"""Analyze this research direction: "{user_query}"

Examples:
- 用户输入: "时间序列异常检测 transformer 方法"
  english_query: "time series anomaly detection transformer methods"
  core_terms: ["time series", "anomaly detection", "transformer"]
- 用户输入: "图神经网络用于根因分析"
  english_query: "graph neural networks for root cause analysis"
  core_terms: ["graph neural networks", "root cause analysis"]

Return JSON with this schema:
{{
  "direction_zh": "Chinese direction name, if applicable",
  "direction_en": "English direction name",
  "english_query": "best single English academic search query",
  "query_variants": ["variant query 1", "variant query 2"],
  "core_terms": ["core term 1", "core term 2"],
  "related_terms": ["related term"],
  "exclude_terms": ["noise term to exclude"],
  "search_intents": ["SURVEY", "FOUNDATIONAL", "SOTA"],
  "sub_directions": ["sub direction"],
  "is_cross_domain": false,
  "domain_components": []
}}""",
        )

        response = await self.llm.chat(messages)
        data = parse_llm_json(response.content)

        direction_en = str(data.get("direction_en") or data.get("english_query") or "").strip()
        english_query = str(data.get("english_query") or direction_en).strip()
        if not english_query:
            raise QueryPlanningError("LLM query plan missing english_query/direction_en")

        return QueryPlan(
            user_query=user_query,
            language="zh" if _is_chinese(user_query) else "en",
            direction_zh=str(data.get("direction_zh") or (user_query if _is_chinese(user_query) else "")),
            direction_en=direction_en or english_query,
            english_query=english_query,
            query_variants=_list_of_str(data.get("query_variants")),
            core_terms=_list_of_str(data.get("core_terms")),
            related_terms=_list_of_str(data.get("related_terms")),
            exclude_terms=_list_of_str(data.get("exclude_terms")),
            search_intents=_parse_intents(_list_of_str(data.get("search_intents")) or ["GENERAL"]),
            sub_directions=_list_of_str(data.get("sub_directions")),
            is_cross_domain=bool(data.get("is_cross_domain", False)),
            domain_components=_list_of_str(data.get("domain_components")),
        )


def _parse_intents(raw: list[str]) -> list[SearchIntent]:
    result: list[SearchIntent] = []
    for item in raw:
        try:
            result.append(SearchIntent(item))
        except ValueError:
            logger.warning("Unknown search intent '%s', skipping", item)
    return result or [SearchIntent.GENERAL]


def _list_of_str(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _is_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)
