from __future__ import annotations

from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion, EvidenceIndex, PaperSkeleton


METHOD_SECTIONS = {"method", "methods", "approach", "model", "architecture"}
EXPERIMENT_SECTIONS = {"experiments", "experiment", "results", "evaluation", "benchmark"}
INTRODUCTION_SECTIONS = {"introduction", "intro"}
LIMITATION_SECTIONS = {"limitations", "limitation", "discussion", "threats_to_validity"}


def build_paper_skeleton(document: DocumentIngestion, evidence_index: EvidenceIndex) -> PaperSkeleton:
    title_block = _first_title_block(document)
    abstract_block = _first_text_block(document, {"abstract"})
    problem_block = _first_text_block(document, INTRODUCTION_SECTIONS)
    method_block = _first_text_block(document, METHOD_SECTIONS)
    experiment_block = _first_text_block(document, EXPERIMENT_SECTIONS)
    limitation_block = _first_text_block(document, LIMITATION_SECTIONS)
    formula_blocks = [block for block in document.blocks if block.type == BlockType.FORMULA]

    warnings = _warnings(document, evidence_index, problem_block, method_block, experiment_block, limitation_block)
    evidence_refs = _valid_evidence_refs(document, evidence_index)

    return PaperSkeleton(
        paper_id=document.paper_id,
        title=_safe_text(title_block, "UNKNOWN"),
        abstract_summary=_safe_text(abstract_block, "UNKNOWN"),
        problem=_safe_text(problem_block, "INSUFFICIENT_EVIDENCE"),
        method_overview=_safe_text(method_block, "INSUFFICIENT_EVIDENCE"),
        experiment_overview=_safe_text(experiment_block, "INSUFFICIENT_EVIDENCE"),
        formulas=[_quote(block.text) for block in formula_blocks],
        limitations=_safe_text(limitation_block, "NEEDS_HUMAN_CHECK"),
        evidence_refs=evidence_refs,
        confidence=_confidence(abstract_block, problem_block, method_block, experiment_block, limitation_block, formula_blocks),
        warnings=warnings,
    )


def _first_title_block(document: DocumentIngestion) -> DocumentBlock | None:
    for block in document.blocks:
        if block.type == BlockType.TITLE:
            return block
    for block in document.blocks:
        if block.type == BlockType.HEADING:
            return block
    return None


def _first_text_block(document: DocumentIngestion, sections: set[str]) -> DocumentBlock | None:
    for block in document.blocks:
        if _section(block) in sections and block.type in {BlockType.ABSTRACT, BlockType.PARAGRAPH}:
            return block
    return None


def _warnings(
    document: DocumentIngestion,
    evidence_index: EvidenceIndex,
    problem_block: DocumentBlock | None,
    method_block: DocumentBlock | None,
    experiment_block: DocumentBlock | None,
    limitation_block: DocumentBlock | None,
) -> list[str]:
    warnings = {warning.code for warning in document.warnings}
    warnings.update(evidence_index.warnings)
    if problem_block is None:
        warnings.add("PROBLEM_SECTION_MISSING")
    if method_block is None:
        warnings.add("METHOD_SECTION_MISSING")
    if experiment_block is None:
        warnings.add("EXPERIMENT_SECTION_MISSING")
    if limitation_block is None:
        warnings.add("LIMITATIONS_SECTION_MISSING")
    if not any(block.type == BlockType.FORMULA for block in document.blocks):
        warnings.add("FORMULA_UNAVAILABLE")
    return sorted(warnings)


def _valid_evidence_refs(document: DocumentIngestion, evidence_index: EvidenceIndex) -> list[str]:
    block_ids = {block.block_id for block in document.blocks}
    refs: list[str] = []
    for claim in evidence_index.claims:
        if claim.block_id in block_ids and claim.evidence_ref not in refs:
            refs.append(claim.evidence_ref)
    return refs


def _confidence(
    abstract_block: DocumentBlock | None,
    problem_block: DocumentBlock | None,
    method_block: DocumentBlock | None,
    experiment_block: DocumentBlock | None,
    limitation_block: DocumentBlock | None,
    formula_blocks: list[DocumentBlock],
) -> float:
    score = 0.0
    if abstract_block is not None:
        score += 0.15
    if problem_block is not None:
        score += 0.15
    if method_block is not None:
        score += 0.15
    if experiment_block is not None:
        score += 0.15
    if formula_blocks:
        score += 0.05
    if limitation_block is not None:
        score += 0.05
    return min(round(score, 2), 0.65)


def _safe_text(block: DocumentBlock | None, fallback: str) -> str:
    if block is None:
        return fallback
    return _quote(block.text)


def _section(block: DocumentBlock) -> str:
    return block.section.strip().lower().replace(" ", "_")


def _quote(text: str, limit: int = 360) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
