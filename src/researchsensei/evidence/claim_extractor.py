from __future__ import annotations

import re

from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.document import DocumentIngestion
from researchsensei.schemas.evidence import (
    ClaimEvidenceBundle,
    ClaimEvidenceRecord,
    Passage,
    PassageIndex,
)

METHOD_SECTIONS = {
    "method", "methods", "approach", "model", "architecture",
    "methodology", "proposed method", "proposed approach",
    "framework", "algorithm", "proposed model",
}
RESULT_SECTIONS = {
    "experiments", "experiment", "results", "evaluation", "benchmark",
    "empirical study", "ablation study", "case study",
}
LIMITATION_SECTIONS = {"limitations", "limitation", "discussion"}

# Section names that contain method-related keywords should also be treated as method sections.
_METHOD_SECTION_KEYWORDS = re.compile(
    r"(method|approach|model|framework|architecture|algorithm|encoder|decoder|"
    r"network|module|layer|block|mixer|transformer|proposed|pipeline|mechanism|"
    r"design|loss|objective|training|learning|embedding|attention)",
    re.IGNORECASE,
)

# Section names that indicate survey/review — should NOT be treated as method.
_SURVEY_SECTION_KEYWORDS = re.compile(
    r"(survey|review|related work|background|preliminar|notation)",
    re.IGNORECASE,
)
CONTRIBUTION_KEYWORDS = re.compile(
    r"\b(propose|present|introduce|develop|contribut)\w*\b", re.IGNORECASE
)
PROBLEM_KEYWORDS = re.compile(
    r"\b(problem|challenge|issue|difficult|limitation)\b", re.IGNORECASE
)
DEFINITION_KEYWORDS = re.compile(
    r"\b(defined\s+as|definition|refers?\s+to|we\s+define)\b", re.IGNORECASE
)
METHOD_KEYWORDS = [
    "propose", "present", "introduce", "method", "model", "framework",
    "approach", "architecture", "design", "mechanism",
]
RESULT_KEYWORDS = [
    "achieve", "outperform", "improve", "result", "performance",
    "accuracy", "f1", "benchmark", "evaluate", "demonstrate",
]


def build_claim_evidence(
    document: DocumentIngestion,
    passage_index: PassageIndex,
) -> ClaimEvidenceBundle:
    paper_id = document.paper_id
    blocks_by_id = {block.block_id: block for block in document.blocks}
    claims: list[ClaimEvidenceRecord] = []
    warnings: list[WarningItem] = []
    counter = 0

    for passage in passage_index.passages:
        section = passage.section.lower().strip()
        block_types_lower = {bt.lower() for bt in passage.source_block_types}

        # Formula passage
        if "formula" in block_types_lower:
            counter += 1
            claims.append(_make_claim(
                paper_id, counter, passage,
                blocks_by_id=blocks_by_id,
                claim_type="FORMULA_CONTEXT",
                semantic_support="DIRECT_QUOTE",
                source_sentence=passage.text[:300],
            ))
            continue

        # Method section (exact match or fuzzy match on section name)
        is_method_section = (
            section in METHOD_SECTIONS
            or (
                section
                and _METHOD_SECTION_KEYWORDS.search(section)
                and not _SURVEY_SECTION_KEYWORDS.search(section)
            )
        )
        if is_method_section:
            counter += 1
            sentence = _find_sentence_with_keywords(passage.text, METHOD_KEYWORDS)
            claims.append(_make_claim(
                paper_id, counter, passage,
                blocks_by_id=blocks_by_id,
                claim_type="METHOD",
                semantic_support="DIRECT_QUOTE" if sentence else "PARAPHRASE",
                source_sentence=sentence or passage.text[:300],
            ))
            continue

        # Result section (exact match or fuzzy match)
        is_result_section = (
            section in RESULT_SECTIONS
            or (
                section
                and re.search(r"(experiment|result|evaluation|benchmark|ablation|study|comparison)", section, re.IGNORECASE)
                and not _SURVEY_SECTION_KEYWORDS.search(section)
            )
        )
        if is_result_section:
            counter += 1
            sentence = _find_sentence_with_keywords(passage.text, RESULT_KEYWORDS)
            claims.append(_make_claim(
                paper_id, counter, passage,
                blocks_by_id=blocks_by_id,
                claim_type="RESULT",
                semantic_support="DIRECT_QUOTE" if sentence else "PARAPHRASE",
                source_sentence=sentence or passage.text[:300],
            ))
            continue

        # Limitation section
        if section in LIMITATION_SECTIONS:
            counter += 1
            claims.append(_make_claim(
                paper_id, counter, passage,
                blocks_by_id=blocks_by_id,
                claim_type="LIMITATION",
                semantic_support="PARAPHRASE",
                source_sentence=passage.text[:300],
            ))
            continue

        # Abstract / introduction with contribution keywords
        if section in ("abstract", "introduction", "intro"):
            sentence = _find_sentence_with_regex(passage.text, CONTRIBUTION_KEYWORDS)
            if sentence:
                counter += 1
                claims.append(_make_claim(
                    paper_id, counter, passage,
                    blocks_by_id=blocks_by_id,
                    claim_text=sentence,
                    claim_type="CONTRIBUTION",
                    semantic_support="DIRECT_QUOTE",
                    source_sentence=sentence,
                ))
                continue

            # Problem in introduction
            if section in ("introduction", "intro"):
                sentence = _find_sentence_with_regex(passage.text, PROBLEM_KEYWORDS)
                if sentence:
                    counter += 1
                    claims.append(_make_claim(
                        paper_id, counter, passage,
                        blocks_by_id=blocks_by_id,
                        claim_text=sentence,
                        claim_type="PROBLEM",
                        semantic_support="DIRECT_QUOTE",
                        source_sentence=sentence,
                    ))
                    continue

        # Definition anywhere
        sentence = _find_sentence_with_regex(passage.text, DEFINITION_KEYWORDS)
        if sentence:
            counter += 1
            claims.append(_make_claim(
                paper_id, counter, passage,
                blocks_by_id=blocks_by_id,
                claim_type="DEFINITION",
                semantic_support="DIRECT_QUOTE",
                source_sentence=sentence,
            ))
            continue

    # Fallback: if no METHOD claim found, try to extract from unclaimed passages
    has_method = any(c.claim_type == "METHOD" for c in claims)
    if not has_method:
        claimed_passage_ids = {c.passage_id for c in claims}
        for passage in passage_index.passages:
            if passage.passage_id in claimed_passage_ids:
                continue
            block_types_lower = {bt.lower() for bt in passage.source_block_types}
            if "formula" in block_types_lower:
                continue
            sentence = _find_sentence_with_keywords(passage.text, METHOD_KEYWORDS)
            if sentence:
                counter += 1
                claims.append(_make_claim(
                    paper_id, counter, passage,
                    blocks_by_id=blocks_by_id,
                    claim_type="METHOD",
                    semantic_support="PARAPHRASE",
                    source_sentence=sentence,
                ))
                break  # One fallback METHOD claim is enough

    if not claims:
        warnings.append(
            WarningItem(code="NO_CLAIMS", message="No claims could be extracted from the passages.")
        )

    return ClaimEvidenceBundle(
        paper_id=paper_id,
        claims=claims,
        warnings=warnings,
        source_artifacts=["passage_index.json", "parsed_document.json"],
    )


def _make_claim(
    paper_id: str,
    counter: int,
    passage: Passage,
    *,
    blocks_by_id: dict,
    claim_type: str,
    semantic_support: str,
    source_sentence: str,
    claim_text: str | None = None,
) -> ClaimEvidenceRecord:
    evidence_ref = passage.evidence_refs[0] if passage.evidence_refs else ""
    block_id = passage.block_ids[0] if passage.block_ids else ""
    block = blocks_by_id.get(block_id)
    return ClaimEvidenceRecord(
        claim_id=f"{paper_id}:claim:c{counter:03d}",
        claim_text=claim_text or source_sentence[:300],
        evidence_ref=evidence_ref,
        block_id=block_id,
        passage_id=passage.passage_id,
        section=passage.section,
        claim_type=claim_type,
        semantic_support=semantic_support,
        source_sentence=source_sentence,
        quote_or_summary=source_sentence[:240],
        confidence=0.6,
        generated_by="rule",
        formula_origin=block.formula_origin if block is not None else "",
        formula_id=block.formula_id if block is not None else "",
        formula_page=block.formula_page if block is not None else None,
        formula_bbox=block.formula_bbox if block is not None else None,
        formula_ocr_status=block.formula_ocr_status if block is not None else "",
        equation_number=block.equation_number if block is not None else "",
        equation_group_id=block.equation_group_id if block is not None else "",
        group_order=block.group_order if block is not None else 0,
        group_crop_path=block.group_crop_path if block is not None else "",
        group_overlay_path=block.group_overlay_path if block is not None else "",
        source_location={
            "pdf_page": block.page if block is not None else None,
            "pdf_bbox": block.bbox if block is not None else None,
        },
        block_source=block.block_source if block is not None else "",
        section_confidence=block.section_confidence if block is not None else "",
        risk_flags=list(block.risk_flags) if block is not None else [],
        parse_quality_status=block.parse_quality_status if block is not None else "",
        fallback_used=block.fallback_used if block is not None else False,
        llama_refined=block.llama_refined if block is not None else False,
    )


def _find_sentence_with_keywords(text: str, keywords: list[str]) -> str | None:
    """Find first sentence containing any of the keywords."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        lower = sentence.lower()
        if any(kw.lower() in lower for kw in keywords):
            return sentence.strip()
    return None


def _find_sentence_with_regex(text: str, pattern: re.Pattern[str]) -> str | None:
    """Find first sentence matching the regex pattern."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if pattern.search(sentence):
            return sentence.strip()
    return None
