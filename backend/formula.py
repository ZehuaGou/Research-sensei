from __future__ import annotations

from backend.llm.client import LLMClient
from backend.llm.prompt_builder import PromptBuilder
from backend.schemas import DocumentBlock, EvidenceType, FormulaCard, FormulaSymbol


class FormulaService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client
        self.prompt_builder = PromptBuilder()

    async def build_formula_card(self, card_id: str, paper_id: str, formula_block: DocumentBlock) -> FormulaCard:
        if self.llm is None:
            return self._fallback(card_id, paper_id, formula_block)
        try:
            nearby = formula_block.nearby_text or ""
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的公式讲解引擎。把 LaTeX 公式讲清楚。"},
                {"role": "user", "content": self.prompt_builder.build_formula_prompt(
                    formula_block.raw_latex or formula_block.text, nearby
                )},
            ]
            data = await self.llm.chat_json(messages, temperature=0.3)
            symbols = [FormulaSymbol(**s) for s in data.get("symbols", [])]
            return FormulaCard(
                card_id=card_id,
                paper_id=paper_id,
                formula_ref=formula_block.block_id,
                formula_latex=formula_block.raw_latex or formula_block.text,
                problem=data.get("problem", ""),
                symbols=symbols,
                numeric_example=data.get("numeric_example", ""),
                remove_effect=data.get("remove_effect", ""),
                weight_change_effect=data.get("weight_change_effect", ""),
                plain_summary=data.get("plain_summary", ""),
                evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
            )
        except Exception as e:
            print(f"[WARN] FormulaService LLM failed, using fallback: {e}")
            return self._fallback(card_id, paper_id, formula_block)

    def _fallback(self, card_id: str, paper_id: str, block: DocumentBlock) -> FormulaCard:
        formula = block.raw_latex or block.text
        symbols = [FormulaSymbol(symbol="L", meaning="总损失或优化目标", role="告诉模型整体要优化什么")]
        if "lambda" in formula.lower():
            symbols.append(FormulaSymbol(symbol="lambda", meaning="正则项权重", role="控制约束项影响大小"))
        return FormulaCard(
            card_id=card_id,
            paper_id=paper_id,
            formula_ref=block.block_id,
            formula_latex=formula,
            problem="这个公式想把论文的核心机制变成可优化目标。",
            symbols=symbols,
            numeric_example="例如 L_task=2, L_reg=0.5, lambda=0.1，则 L=2+0.1*0.5=2.05。",
            remove_effect="如果去掉约束项，模型可能只追求训练误差，泛化和结构稳定性变弱。",
            weight_change_effect="lambda 变大时更重视约束，变小时更重视任务误差。",
            plain_summary="它有效的直觉是：既要完成任务，又要避免学到不稳定的捷径。",
            evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
        )
