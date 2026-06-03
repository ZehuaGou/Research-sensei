from __future__ import annotations

from backend.llm.client import LLMClient
from backend.schemas import CardType, PaperSkeleton, TeachingCard


class TeachingService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    async def build_paper_card(self, skeleton: PaperSkeleton) -> TeachingCard:
        if self.llm is None:
            return self._fallback(skeleton)
        try:
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的教学引擎。根据论文骨架生成五层讲解。中文为主。"},
                {"role": "user", "content": f"""根据论文骨架生成教学卡片。

论文骨架:
{skeleton.model_dump_json()[:4000]}

要求输出 JSON:
{{
  "thirty_second": "一句话说清论文在做什么，为什么重要",
  "five_minute": "用类比和直觉讲解核心机制，200-300字",
  "deep_dive": "详细推导和分析，包含公式解释"
}}"""},
            ]
            data = await self.llm.chat_json(messages, temperature=0.7)
            return TeachingCard(
                card_id=f"paper_card_{skeleton.paper_id}",
                paper_id=skeleton.paper_id,
                card_type=CardType.PAPER_CARD,
                thirty_second=data.get("thirty_second", ""),
                five_minute=data.get("five_minute", ""),
                deep_dive=data.get("deep_dive", ""),
                evidence_status=skeleton.evidence_status,
            )
        except Exception as e:
            print(f"[WARN] TeachingService LLM failed, using fallback: {e}")
            return self._fallback(skeleton)

    def _fallback(self, skeleton: PaperSkeleton) -> TeachingCard:
        return TeachingCard(
            card_id=f"paper_card_{skeleton.paper_id}",
            paper_id=skeleton.paper_id,
            card_type=CardType.PAPER_CARD,
            thirty_second=skeleton.problem.plain or "待分析",
            five_minute=f"核心机制：{skeleton.mechanism.plain}" if skeleton.mechanism.plain else "需要 LLM 生成详细讲解",
            deep_dive="请配置 LLM 后重新生成",
            evidence_status=skeleton.evidence_status,
        )
