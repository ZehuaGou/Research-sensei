from __future__ import annotations

import logging
import re
from typing import Iterable, Protocol

from researchsensei.acquisition.venue_registry import VENUE_REGISTRY, lookup_venue
from researchsensei.llm.client import parse_llm_json
from researchsensei.llm.prompt_builder import PromptBuilder
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig
from researchsensei.schemas import QueryPlan
from researchsensei.schemas.enums import SearchIntent

logger = logging.getLogger(__name__)


class QueryPlanningError(RuntimeError):
    """Raised when literature discovery cannot produce a real LLM query plan."""


class QueryPlannerClient(Protocol):
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> ChatResponse: ...


class QueryPlanner:
    """Generates structured query plans from user direction input."""

    def __init__(self, llm_client: QueryPlannerClient | None = None) -> None:
        self.llm = llm_client

    async def plan(self, user_query: str) -> QueryPlan:
        """Generate a query plan from user input.

        literature discovery must not silently fall back to heuristic query planning. A missing or
        invalid LLM plan is a real blocker because Chinese research directions
        often need precise English academic query terms.
        """
        if self.llm is None:
            raise QueryPlanningError("LITERATURE_QUERY_PLANNING_REQUIRES_REAL_LLM")

        try:
            return await self._plan_with_llm(user_query)
        except Exception as exc:
            logger.warning("LLM query planning failed: %s", exc)
            raise QueryPlanningError(f"LITERATURE_QUERY_PLANNING_FAILED: {type(exc).__name__}: {exc}") from exc

    async def _plan_with_llm(self, user_query: str) -> QueryPlan:
        llm = self.llm
        if llm is None:
            raise QueryPlanningError("LITERATURE_QUERY_PLANNING_REQUIRES_REAL_LLM")
        prompt_builder = PromptBuilder()
        messages = prompt_builder.build_simple(
            system=(
                "You are ResearchSensei's research-query planning engine.\n"
                "Convert the user's research direction into precise English academic search terms.\n"
                "Preserve every core constraint in the user's query: data type, task, method family, and application domain.\n"
                "Do not broaden the query by dropping task/domain terms. If the user writes Chinese, translate the full phrase.\n"
                "Create complementary variants for discovery coverage: exact task+method, task+domain, terminology/abbreviation, and survey/foundational.\n"
                "Prefer queries that work in arXiv, OpenAlex, and Semantic Scholar; do not make every variant venue-specific.\n"
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
- 用户输入: "异常解释"
  english_query: "explainable anomaly detection"
  core_terms: ["anomaly explanation", "anomaly attribution", "explainable anomaly detection"]

Return JSON with this schema:
{{
  "direction_zh": "Chinese direction name, if applicable",
  "direction_en": "English direction name",
  "english_query": "best single English academic search query",
  "query_variants": ["4-6 complementary queries ordered from exact to broader, without dropping the core task"],
  "core_terms": ["core term 1", "core term 2"],
  "related_terms": ["related term"],
  "exclude_terms": ["noise term to exclude"],
  "search_intents": ["SURVEY", "FOUNDATIONAL", "SOTA"],
  "sub_directions": ["sub direction"],
  "is_cross_domain": false,
  "domain_components": []
}}""",
        )

        response = await llm.chat(messages)
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
            venue_targets=_detect_venue_targets(user_query, _list_of_str(data.get("sub_directions"))),
            venue_openalex_source_ids=[],  # filled in by _detect_venue_targets inside the helper
            year_from=_detect_year(user_query, "from"),
            year_to=_detect_year(user_query, "to"),
        )


# ---------------------------------------------------------------------------
# Venue + year detection helpers
# ---------------------------------------------------------------------------
_YEAR_RANGE_RE = re.compile(r"\b(20\d{2})\s*(?:[-–—至到]\s*(20\d{2}))?")
_YEAR_RECENT_RE = re.compile(r"\b(recent|latest|new|近三年|近年|最新|近期)\b", re.I)


def _detect_venue_targets(raw_query: str, secondary_strings: list[str]) -> list[str]:
    """Scan the user query and LLM-emitted strings for known venue aliases.

    Returns a unique list of canonical_name values (preserving first-match order).
    Populates a module-level side-effect is intentionally avoided: callers can
    re-deriving openalex_source_ids from the returned targets via VENUE_REGISTRY.
    """
    if not raw_query:
        return []
    pools: list[str] = [raw_query.lower()]
    pools.extend((s.lower() for s in secondary_strings if s))

    seen: set[str] = set()
    targets: list[str] = []
    for cfg in VENUE_REGISTRY.values():
        for alias in cfg.aliases:
            if not alias:
                continue
            if any(alias in pool for pool in pools):
                if cfg.canonical_name not in seen:
                    seen.add(cfg.canonical_name)
                    targets.append(cfg.canonical_name)
                break
    return targets


def detect_venue_openalex_source_ids(canonical_targets: Iterable[str]) -> list[str]:
    """Map a list of canonical_name strings to OpenAlex source IDs.

    Used by DirectionExplorationService after the planner has produced venue targets.
    """
    out: list[str] = []
    seen: set[str] = set()
    for target in canonical_targets:
        cfg = lookup_venue(target) or None
        if cfg is None:
            continue
        for sid in cfg.openalex_source_ids:
            if not sid or sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
    return out


def _detect_year(raw_query: str, boundary: str) -> int | None:
    """Return a year integer for the requested boundary, or None if no year hint.

    boundary: "from" returns the earliest year; "to" returns the latest.
    Multiplicity: "2023-2024" -> from=2023, to=2024. "2023" -> from=2023, to=2023.
    """
    if not raw_query:
        return None
    match = _YEAR_RANGE_RE.search(raw_query)
    if match:
        first = int(match.group(1))
        second = match.group(2)
        if second:
            return first if boundary == "from" else int(second)
        return first
    # "recent" / "latest" / 最新 -> widen year window to last 3 years.
    if _YEAR_RECENT_RE.search(raw_query):
        import datetime
        current_year = datetime.date.today().year
        return current_year - 2 if boundary == "from" else current_year
    return None


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
