from __future__ import annotations

from researchsensei.schemas import (
    BlockType,
    ClaimEvidence,
    DocumentBlock,
    DocumentIngestion,
    EvidenceIndex,
    EvidenceType,
)


METHOD_SECTIONS = {"method", "methods", "approach", "model", "architecture"}
EXPERIMENT_SECTIONS = {"experiments", "experiment", "results", "evaluation", "benchmark"}
INTRODUCTION_SECTIONS = {"introduction", "intro"}


def build_evidence_index(document: DocumentIngestion) -> EvidenceIndex:
    claims: list[ClaimEvidence] = []
    warnings: list[str] = []

    if not document.blocks:
        return EvidenceIndex(
            paper_id=document.paper_id,
            claims=[],
            warnings=["NO_BLOCKS_AVAILABLE", "INSUFFICIENT_EVIDENCE"],
        )

    for block in document.blocks:
        claim = _claim_from_block(document.paper_id, block)
        if claim is not None:
            claims.append(claim)

    claims.extend(_missing_structure_claims(document))

    if not any(block.type == BlockType.FORMULA for block in document.blocks):
        warnings.append("FORMULA_UNAVAILABLE")
    if not _has_section(document, METHOD_SECTIONS):
        warnings.append("METHOD_SECTION_MISSING")
    if not _has_section(document, EXPERIMENT_SECTIONS):
        warnings.append("EXPERIMENT_SECTION_MISSING")

    return EvidenceIndex(paper_id=document.paper_id, claims=claims, warnings=warnings)


def _claim_from_block(paper_id: str, block: DocumentBlock) -> ClaimEvidence | None:
    section = _section(block)
    if block.type == BlockType.TITLE:
        return _claim(
            paper_id,
            block,
            "title",
            "This block is a title candidate.",
            EvidenceType.SUPPORTED_BY_TEXT,
            0.75,
        )
    if block.type == BlockType.ABSTRACT or section == "abstract":
        return _claim(
            paper_id,
            block,
            "abstract",
            "This block is abstract-section text.",
            EvidenceType.SUPPORTED_BY_TEXT,
            0.7,
        )
    if block.type == BlockType.FORMULA:
        return _claim(
            paper_id,
            block,
            "formula",
            "This block contains a formula candidate.",
            EvidenceType.SUPPORTED_BY_FORMULA,
            0.7,
        )
    if block.type == BlockType.TABLE:
        return _claim(
            paper_id,
            block,
            "table",
            "This block is a table candidate and needs human verification.",
            EvidenceType.NEEDS_HUMAN_CHECK,
            0.4,
        )
    if block.type == BlockType.FIGURE:
        return _claim(
            paper_id,
            block,
            "figure",
            "This block is a figure candidate and needs human verification.",
            EvidenceType.NEEDS_HUMAN_CHECK,
            0.4,
        )
    if section in EXPERIMENT_SECTIONS:
        return _claim(
            paper_id,
            block,
            "experiment",
            "This block belongs to an experiments/results section.",
            EvidenceType.SUPPORTED_BY_EXPERIMENT,
            0.65,
        )
    if section in METHOD_SECTIONS:
        return _claim(
            paper_id,
            block,
            "method",
            "This block belongs to a method/model section.",
            EvidenceType.SUPPORTED_BY_TEXT,
            0.65,
        )
    if section in INTRODUCTION_SECTIONS:
        return _claim(
            paper_id,
            block,
            "introduction",
            "This block belongs to an introduction section.",
            EvidenceType.SUPPORTED_BY_TEXT,
            0.6,
        )
    return None


def _missing_structure_claims(document: DocumentIngestion) -> list[ClaimEvidence]:
    anchor = _first_block(document)
    if anchor is None:
        return []

    claims: list[ClaimEvidence] = []
    if not _has_section(document, METHOD_SECTIONS):
        claims.append(
            _claim(
                document.paper_id,
                anchor,
                "missing-method",
                "No method/model section was detected in the parsed blocks.",
                EvidenceType.INSUFFICIENT_EVIDENCE,
                0.2,
                claim_id=f"{document.paper_id}-missing-method",
            )
        )
    if not _has_section(document, EXPERIMENT_SECTIONS):
        claims.append(
            _claim(
                document.paper_id,
                anchor,
                "missing-experiments",
                "No experiments/results section was detected in the parsed blocks.",
                EvidenceType.INSUFFICIENT_EVIDENCE,
                0.2,
                claim_id=f"{document.paper_id}-missing-experiments",
            )
        )
    if not any(block.type == BlockType.FORMULA for block in document.blocks):
        claims.append(
            _claim(
                document.paper_id,
                anchor,
                "missing-formulas",
                "No formula block was detected in the parsed blocks.",
                EvidenceType.NEEDS_HUMAN_CHECK,
                0.25,
                claim_id=f"{document.paper_id}-missing-formulas",
            )
        )
    return claims


def _claim(
    paper_id: str,
    block: DocumentBlock,
    claim_kind: str,
    claim_text: str,
    evidence_type: EvidenceType,
    confidence: float,
    *,
    claim_id: str | None = None,
) -> ClaimEvidence:
    return ClaimEvidence(
        claim_id=claim_id or f"{paper_id}-{claim_kind}-{block.block_id}",
        claim_text=claim_text,
        evidence_type=evidence_type,
        evidence_ref=block.evidence_ref,
        block_id=block.block_id,
        section=block.section,
        quote_or_summary=_quote(block.text),
        confidence=confidence,
    )


def _has_section(document: DocumentIngestion, section_names: set[str]) -> bool:
    return any(_section(block) in section_names for block in document.blocks)


def _section(block: DocumentBlock) -> str:
    return block.section.strip().lower().replace(" ", "_")


def _first_block(document: DocumentIngestion) -> DocumentBlock | None:
    return document.blocks[0] if document.blocks else None


def _quote(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
