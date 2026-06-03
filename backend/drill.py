from __future__ import annotations

from backend.llm.client import LLMClient
from backend.llm.prompt_builder import PromptBuilder
from backend.schemas import DrillCard, PaperSkeleton


class DrillService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client
        self.prompt_builder = PromptBuilder()

    async def build_drill_card(self, skeleton: PaperSkeleton, memory: dict | None = None) -> DrillCard:
        if self.llm is None:
            return self._fallback(skeleton)
        try:
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的训练引擎。生成有深度的训练题。"},
                {"role": "user", "content": self.prompt_builder.build_drill_prompt(
                    skeleton.model_dump(), memory
                )},
            ]
            data = await self.llm.chat_json(messages, temperature=0.7)
            return DrillCard(
                card_id=f"drill_{skeleton.paper_id}",
                target=skeleton.paper_id,
                recall_questions=[q["question"] for q in data.get("immediate_recall", [])],
                advisor_questions=[q["question"] for q in data.get("advisor_questions", [])],
                error_attribution_prompts=[q["question"] for q in data.get("weakness_checks", [])],
            )
        except Exception as e:
            print(f"[WARN] DrillService LLM failed, using fallback: {e}")
            return self._fallback(skeleton)

    def _fallback(self, skeleton: PaperSkeleton) -> DrillCard:
        return DrillCard(
            card_id=f"drill_{skeleton.paper_id}",
            target=skeleton.paper_id,
            recall_questions=[
                "用自己的话说出论文解决的问题。",
                "旧方法的真实瓶颈是什么？",
                "核心机制为什么可能有效？",
            ],
            advisor_questions=[
                "如果去掉关键 loss 项会怎样？",
                "实验是否真的支持主要 claim？",
            ],
            error_attribution_prompts=[
                "如果你只回答'效果更好'，错误原因是没有解释机制。",
            ],
        )
