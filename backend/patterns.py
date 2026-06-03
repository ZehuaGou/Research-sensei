from __future__ import annotations

from backend.llm.client import LLMClient
from backend.llm.prompt_builder import PromptBuilder
from backend.schemas import PaperSkeleton, PatternCard


class PatternService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client
        self.prompt_builder = PromptBuilder()

    async def build_pattern_card(self, card_id: str, pattern_id: str, skeleton: PaperSkeleton) -> PatternCard:
        if self.llm is None:
            return self._fallback(card_id, pattern_id)
        try:
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的科研模式分析引擎。"},
                {"role": "user", "content": self.prompt_builder.build_pattern_prompt(skeleton.model_dump())},
            ]
            data = await self.llm.chat_json(messages, temperature=0.3)
            return PatternCard(
                card_id=card_id,
                pattern_id=pattern_id,
                definition=data.get("definition", ""),
                signals=data.get("signals", [data.get("why_this_pattern", "")]),
                transfer_template=data.get("transfer_guidance", data.get("transfer_template", "")),
            )
        except Exception as e:
            print(f"[WARN] PatternService LLM failed, using fallback: {e}")
            return self._fallback(card_id, pattern_id)

    def _fallback(self, card_id: str, pattern_id: str) -> PatternCard:
        return PatternCard(
            card_id=card_id,
            pattern_id=pattern_id,
            definition="把论文创新归入通用科研模式，便于迁移到其他方向。",
            signals=["表示变化", "目标函数变化", "结构建模变化", "评估协议变化"],
            transfer_template="在新问题中检查：对象如何表示、约束如何定义、证据如何验证。",
        )
