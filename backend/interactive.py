from __future__ import annotations

from backend.llm.client import LLMClient
from backend.llm.prompt_builder import PromptBuilder
from backend.schemas import EvidenceType, InteractiveAnswer, InteractiveContextPackage


class InteractiveService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client
        self.prompt_builder = PromptBuilder()

    async def answer(self, package: InteractiveContextPackage) -> InteractiveAnswer:
        if self.llm is None:
            return self._fallback(package)
        try:
            prompt = self.prompt_builder.build_interactive_prompt(package)
            messages = [
                {"role": "system", "content": self.prompt_builder.build_interactive_system_prompt(package)},
                {"role": "user", "content": prompt},
            ]
            data = await self.llm.chat_json(messages, temperature=0.7)
            return InteractiveAnswer(
                answer_zh=data.get("answer", data.get("answer_zh", "")),
                context_used=package,
                evidence_status=EvidenceType.REASONABLE_INFERENCE,
                add_to_review_suggestion=False,
            )
        except Exception as e:
            print(f"[WARN] InteractiveService LLM failed, using fallback: {e}")
            return self._fallback(package)

    def _fallback(self, package: InteractiveContextPackage) -> InteractiveAnswer:
        selected = package.selected_text or "当前内容"
        answer = (
            f"先看直觉：{selected} 是当前卡片里的关键点。"
            "如果它是公式项，通常要问三件事：它惩罚什么、鼓励什么、权重变大变小会怎样。"
            "证据不足时需要回到原文对应 evidence chunk 人工核验。"
        )
        return InteractiveAnswer(
            answer_zh=answer,
            context_used=package,
            evidence_status=EvidenceType.REASONABLE_INFERENCE,
            add_to_review_suggestion=True,
        )
