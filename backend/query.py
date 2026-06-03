from __future__ import annotations

from backend.llm.client import LLMClient
from backend.schemas import QueryPlan, SearchIntent


class QueryService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    async def understand(self, user_query: str) -> QueryPlan:
        if self.llm is None:
            return self._fallback(user_query)
        try:
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的方向分析引擎。分析用户的研究方向，输出 JSON。"},
                {"role": "user", "content": f"""分析这个研究方向: "{user_query}"

输出 JSON 格式:
{{
  "direction_zh": "中文方向名",
  "direction_en": "English direction name",
  "core_terms": ["核心术语1", "core term 2"],
  "related_terms": ["相关术语"],
  "exclude_terms": ["应排除的噪声"],
  "search_intents": ["SURVEY_PAPER", "FOUNDATIONAL_WORK", "CLASSIC_METHOD", "SOTA_METHOD"],
  "sub_directions": [],
  "is_cross_domain": false,
  "domain_components": []
}}"""},
            ]
            data = await self.llm.chat_json(messages, temperature=0.3)
            intents = []
            for intent_str in data.get("search_intents", []):
                try:
                    intents.append(SearchIntent(intent_str))
                except ValueError:
                    pass
            return QueryPlan(
                user_query=user_query,
                language="zh" if any(ord(c) > 127 for c in user_query) else "en",
                direction_zh=data.get("direction_zh", user_query),
                direction_en=data.get("direction_en", user_query),
                core_terms=data.get("core_terms", []),
                related_terms=data.get("related_terms", []),
                exclude_terms=data.get("exclude_terms", []),
                search_intents=intents,
                sub_directions=data.get("sub_directions", []),
                is_cross_domain=data.get("is_cross_domain", False),
                domain_components=data.get("domain_components", []),
            )
        except Exception as e:
            print(f"[WARN] QueryService LLM failed, using fallback: {e}")
            return self._fallback(user_query)

    def _fallback(self, query: str) -> QueryPlan:
        is_zh = any(ord(c) > 127 for c in query)
        return QueryPlan(
            user_query=query,
            language="zh" if is_zh else "en",
            direction_zh=query if is_zh else "",
            direction_en=query if not is_zh else query,
            core_terms=[query],
            related_terms=[],
            exclude_terms=[],
            search_intents=[
                SearchIntent.SURVEY_PAPER,
                SearchIntent.CLASSIC_METHOD,
                SearchIntent.SOTA_METHOD,
            ],
        )
