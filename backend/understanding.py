from __future__ import annotations

from backend.llm.client import LLMClient
from backend.schemas import (
    DocumentIngestion,
    EvidenceIndex,
    EvidenceType,
    ObjectiveItem,
    PaperSkeleton,
    SkeletonField,
)


SUPPORTED_EVIDENCE_TYPES = {
    EvidenceType.SUPPORTED_BY_TEXT,
    EvidenceType.SUPPORTED_BY_FORMULA,
    EvidenceType.SUPPORTED_BY_EXPERIMENT,
}


class UnderstandingService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    async def build_skeleton(self, doc: DocumentIngestion, evidence: EvidenceIndex) -> PaperSkeleton:
        if self.llm is None:
            return self._fallback_skeleton(doc, evidence)
        try:
            sections_text = "\n".join(
                f"## {k}\n{v[:2000]}" for k, v in doc.sections.items() if v
            )
            messages = [
                {"role": "system", "content": "你是 ResearchSensei 的论文理解引擎。从论文内容中提取骨架信息，输出 JSON。"},
                {"role": "user", "content": f"""分析这篇论文，提取核心骨架。

论文内容:
{sections_text[:6000]}

输出 JSON:
{{
  "problem": {{"plain": "通俗描述", "technical": "技术描述", "evidence": []}},
  "old_methods": [{{"name": "", "description": "", "limitation": ""}}],
  "bottleneck": [{{"description": "", "why_critical": ""}}],
  "assumption": [{{"description": "", "justification": ""}}],
  "representation": [{{"description": "", "how_different": ""}}],
  "mechanism": {{"plain": "", "technical": "", "evidence": []}},
  "objective": [{{"formula_ref": "", "purpose": "", "why_this_form": ""}}],
  "experiments": [{{"description": "", "what_proves": "", "limitations": ""}}],
  "limitations": [],
  "transfer": [{{"idea": "", "potential_directions": []}}],
  "pattern_candidates": []
}}"""},
            ]
            data = await self.llm.chat_json(messages, temperature=0.3)
            return self._parse_skeleton(doc.paper_id, data, evidence)
        except Exception as e:
            print(f"[WARN] UnderstandingService LLM failed, using fallback: {e}")
            return self._fallback_skeleton(doc, evidence)

    def _parse_skeleton(self, paper_id: str, data: dict, evidence: EvidenceIndex) -> PaperSkeleton:
        evidence_status = self._overall_evidence_status(evidence)
        problem_data = data.get("problem", {})
        mechanism_data = data.get("mechanism", {})
        objective_items = []
        for o in data.get("objective", []):
            objective_items.append(ObjectiveItem(
                formula_ref=o.get("formula_ref", ""),
                purpose=o.get("purpose", ""),
                why_this_form=o.get("why_this_form", ""),
            ))
        return PaperSkeleton(
            paper_id=paper_id,
            evidence_status=evidence_status,
            problem=SkeletonField(
                plain=problem_data.get("plain", ""),
                technical=problem_data.get("technical", ""),
                evidence=problem_data.get("evidence", []),
            ),
            old_methods=data.get("old_methods", []),
            bottleneck=data.get("bottleneck", []),
            assumption=data.get("assumption", []),
            representation=data.get("representation", []),
            mechanism=SkeletonField(
                plain=mechanism_data.get("plain", ""),
                technical=mechanism_data.get("technical", ""),
                evidence=mechanism_data.get("evidence", []),
            ),
            objective=objective_items,
            experiments=data.get("experiments", []),
            limitations=data.get("limitations", []),
            transfer=data.get("transfer", []),
            pattern_candidates=data.get("pattern_candidates", []),
        )

    def _fallback_skeleton(self, doc: DocumentIngestion, evidence: EvidenceIndex) -> PaperSkeleton:
        evidence_status = self._overall_evidence_status(evidence)
        abstract = doc.sections.get("abstract", "")[:500]
        supported_refs = [
            claim.evidence_ref
            for claim in evidence.claims
            if claim.evidence_type in SUPPORTED_EVIDENCE_TYPES
        ][:3]
        formula_ref = doc.formulas[0].block_id if doc.formulas else ""
        method_text = doc.sections.get("method", "")

        # Generate problem from abstract
        problem_plain = abstract[:150].strip() if abstract else "需要上传全文后分析"
        if len(abstract) > 150:
            problem_plain += "..."

        # Generate mechanism from method section
        if method_text:
            mechanism_plain = method_text[:200].strip()
            if len(method_text) > 200:
                mechanism_plain += "..."
        else:
            mechanism_plain = "需要上传全文 PDF 后进行深度分析"

        return PaperSkeleton(
            paper_id=doc.paper_id,
            evidence_status=evidence_status,
            problem=SkeletonField(
                plain=problem_plain,
                technical=abstract or "摘要不足",
                evidence=supported_refs,
            ),
            mechanism=SkeletonField(
                plain=mechanism_plain,
                technical=method_text[:500] or "需要人工核验：method section 缺失。",
                evidence=supported_refs,
            ),
            objective=[ObjectiveItem(
                formula_ref=formula_ref,
                purpose="把任务误差和结构约束合成一个可训练目标。",
                why_this_form="不同 loss 项分别约束预测/重构能力与结构稳定性。",
            )] if formula_ref else [],
            limitations=["需要 LLM 分析"],
        )

    def _overall_evidence_status(self, evidence: EvidenceIndex) -> EvidenceType:
        types = [claim.evidence_type for claim in evidence.claims]
        if any(item in SUPPORTED_EVIDENCE_TYPES for item in types):
            if EvidenceType.SUPPORTED_BY_EXPERIMENT in types:
                return EvidenceType.SUPPORTED_BY_EXPERIMENT
            if EvidenceType.SUPPORTED_BY_FORMULA in types:
                return EvidenceType.SUPPORTED_BY_FORMULA
            return EvidenceType.SUPPORTED_BY_TEXT
        if EvidenceType.NEEDS_HUMAN_CHECK in types:
            return EvidenceType.NEEDS_HUMAN_CHECK
        if types:
            return EvidenceType.INSUFFICIENT_EVIDENCE
        return EvidenceType.UNVERIFIED
