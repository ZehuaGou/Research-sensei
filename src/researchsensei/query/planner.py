from __future__ import annotations

import logging

from researchsensei.llm.client import LLMClient, MockLLMClient, parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.schemas import QueryPlan
from researchsensei.schemas.enums import SearchIntent

logger = logging.getLogger(__name__)


class QueryPlanner:
    """Generates structured query plans from user direction input."""

    def __init__(self, llm_client: LLMClient | MockLLMClient | None = None) -> None:
        self.llm = llm_client

    async def plan(self, user_query: str) -> QueryPlan:
        """Generate a query plan from user input."""
        if self.llm is not None:
            try:
                return await self._plan_with_llm(user_query)
            except Exception as exc:
                logger.warning("LLM query planning failed, using fallback: %s", exc)

        return self._plan_fallback(user_query)

    async def _plan_with_llm(self, user_query: str) -> QueryPlan:
        """Generate query plan using LLM."""
        prompt_builder = PromptBuilder()
        messages = prompt_builder.build_simple(
            system=(
                "你是 ResearchSensei 的方向分析引擎。\n"
                "分析用户的研究方向，生成结构化查询计划。\n"
                "输出 JSON 格式。"
            ),
            user=f"""分析这个研究方向: "{user_query}"

输出 JSON 格式:
{{
  "direction_zh": "中文方向名",
  "direction_en": "English direction name",
  "core_terms": ["核心术语1", "core term 2"],
  "related_terms": ["相关术语"],
  "exclude_terms": ["应排除的噪声"],
  "search_intents": ["SURVEY", "FOUNDATIONAL", "SOTA"],
  "sub_directions": ["子方向1"],
  "is_cross_domain": false,
  "domain_components": []
}}""",
        )

        response = await self.llm.chat(messages)
        data = parse_llm_json(response.content)

        return QueryPlan(
            user_query=user_query,
            language="zh" if _is_chinese(user_query) else "en",
            direction_zh=data.get("direction_zh", user_query),
            direction_en=data.get("direction_en", user_query),
            core_terms=data.get("core_terms", []),
            related_terms=data.get("related_terms", []),
            exclude_terms=data.get("exclude_terms", []),
            search_intents=_parse_intents(data.get("search_intents", ["GENERAL"])),
            sub_directions=data.get("sub_directions", []),
            is_cross_domain=data.get("is_cross_domain", False),
            domain_components=data.get("domain_components", []),
        )

    def _plan_fallback(self, user_query: str) -> QueryPlan:
        """Generate a conservative fallback query plan without LLM."""
        is_zh = _is_chinese(user_query)

        # Extract core terms by splitting on common separators
        terms = [t.strip() for t in user_query.replace("，", ",").replace("、", ",").split(",") if t.strip()]
        if not terms:
            terms = [user_query]

        warnings = ["RULE_BASED_FALLBACK"]
        direction_en = user_query
        if is_zh:
            warnings.append("CHINESE_QUERY_NO_LLM_FALLBACK")
            warnings.append("EN_QUERY_UNAVAILABLE")
            # Chinese queries without LLM cannot produce English search terms.
            # direction_en stays as Chinese - search engines may return poor results.

        return QueryPlan(
            user_query=user_query,
            language="zh" if is_zh else "en",
            direction_zh=user_query if is_zh else "",
            direction_en=direction_en,
            core_terms=terms,
            related_terms=[],
            exclude_terms=[],
            search_intents=[SearchIntent.SURVEY, SearchIntent.SOTA],
            sub_directions=[],
            is_cross_domain=False,
            domain_components=[],
            warnings=warnings,
        )


def _parse_intents(raw: list[str]) -> list[SearchIntent]:
    """Convert raw string list to SearchIntent list, skipping unknown values."""
    result: list[SearchIntent] = []
    for item in raw:
        try:
            result.append(SearchIntent(item))
        except ValueError:
            logger.warning("Unknown search intent '%s', skipping", item)
    return result or [SearchIntent.GENERAL]


def _is_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return any("一" <= c <= "鿿" for c in text)
