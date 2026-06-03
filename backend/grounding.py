from __future__ import annotations

from backend.schemas import BlockType, DocumentIngestion, EvidenceClaim, EvidenceIndex, EvidenceType


class GroundingService:
    """Build claim/evidence records from parsed blocks.

    Important boundary: metadata-only material is not paper evidence. It can
    suggest a claim to inspect, but it must stay in NEEDS_HUMAN_CHECK until the
    user uploads full text or a resolver provides reliable source blocks.
    """

    def build_index(self, doc: DocumentIngestion) -> EvidenceIndex:
        claims: list[EvidenceClaim] = []
        metadata_only = self._is_metadata_only(doc)
        for block in doc.blocks:
            text = f"{block.text} {block.nearby_text}".strip()
            lowered = text.lower()
            if block.type == BlockType.FORMULA:
                if metadata_only:
                    claims.append(self._needs_human_check_claim(
                        doc,
                        claim_count=len(claims),
                        section=block.section,
                        evidence_ref=block.evidence_ref,
                        summary=block.raw_latex or text[:240],
                        reason="公式只来自搜索元数据或摘要，不能视为论文原文公式。",
                    ))
                    continue
                claims.append(EvidenceClaim(
                    claim_id=f"claim_{len(claims)+1:03d}",
                    claim_text="论文包含一个可用于目标函数或机制解释的公式。",
                    evidence_type=EvidenceType.SUPPORTED_BY_FORMULA,
                    section=block.section,
                    evidence_ref=block.evidence_ref,
                    quote_or_summary=block.raw_latex,
                    confidence=0.9,
                ))
            elif block.section == "experiments" or "table" in lowered or "f1" in lowered:
                if metadata_only:
                    claims.append(self._needs_human_check_claim(
                        doc,
                        claim_count=len(claims),
                        section=block.section,
                        evidence_ref=block.evidence_ref,
                        summary=text[:240],
                        reason="实验 claim 只来自搜索元数据/摘要，缺少全文表格、指标和实验协议证据。",
                    ))
                    continue
                claims.append(EvidenceClaim(
                    claim_id=f"claim_{len(claims)+1:03d}",
                    claim_text="论文实验部分提供了效果证据。",
                    evidence_type=EvidenceType.SUPPORTED_BY_EXPERIMENT,
                    section=block.section,
                    evidence_ref=block.evidence_ref,
                    quote_or_summary=text[:240],
                    confidence=0.8,
                ))
            elif "anomaly" in lowered or "method" in lowered:
                if metadata_only:
                    claims.append(self._needs_human_check_claim(
                        doc,
                        claim_count=len(claims),
                        section=block.section,
                        evidence_ref=block.evidence_ref,
                        summary=text[:240],
                        reason="方法/问题描述只来自搜索元数据或摘要，需要上传全文后核验。",
                    ))
                    continue
                claims.append(EvidenceClaim(
                    claim_id=f"claim_{len(claims)+1:03d}",
                    claim_text="论文围绕异常检测问题或方法机制展开。",
                    evidence_type=EvidenceType.SUPPORTED_BY_TEXT,
                    section=block.section,
                    evidence_ref=block.evidence_ref,
                    quote_or_summary=text[:240],
                    confidence=0.75,
                ))
        return EvidenceIndex(paper_id=doc.paper_id, claims=claims)

    def _is_metadata_only(self, doc: DocumentIngestion) -> bool:
        warning_text = " ".join(doc.extraction_warnings).upper()
        return (
            "METADATA_ONLY_SOURCE" in warning_text
            or "NEEDS_USER_UPLOAD_FULL_TEXT" in warning_text
            or "SOURCE_KIND:METADATA_ONLY" in warning_text
        )

    def _needs_human_check_claim(
        self,
        doc: DocumentIngestion,
        *,
        claim_count: int,
        section: str,
        evidence_ref: str,
        summary: str,
        reason: str,
    ) -> EvidenceClaim:
        return EvidenceClaim(
            claim_id=f"claim_{claim_count+1:03d}",
            claim_text=f"需要人工核验：{reason}",
            evidence_type=EvidenceType.NEEDS_HUMAN_CHECK,
            section=section,
            evidence_ref=evidence_ref or doc.paper_id,
            quote_or_summary=summary,
            confidence=0.2,
        )
