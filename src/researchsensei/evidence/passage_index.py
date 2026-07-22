from __future__ import annotations

import re

from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.document import DocumentBlock, DocumentIngestion
from researchsensei.schemas.enums import BlockType
from researchsensei.schemas.evidence import (
    Passage,
    PassageIndex,
    PassageIndexBuildConfig,
    PassageIndexStats,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
SHORT_EVIDENCE_SECTIONS = {
    "abstract",
    "approach",
    "experiment",
    "experiments",
    "introduction",
    "method",
    "methodology",
    "methods",
    "model",
    "results",
}
SHORT_EVIDENCE_KEYWORDS = re.compile(
    r"\b("
    r"achieve|algorithm|architecture|benchmark|challenge|contribution|evaluate|framework|"
    r"improve|introduce|loss|method|model|module|objective|outperform|problem|propose|"
    r"result|train|training"
    r")\b",
    re.IGNORECASE,
)


def build_passage_index(
    document: DocumentIngestion,
    config: PassageIndexBuildConfig | None = None,
) -> PassageIndex:
    cfg = config or PassageIndexBuildConfig()
    passages: list[Passage] = []
    warnings: list[WarningItem] = []
    paper_id = document.paper_id

    # State for merging
    buffer_blocks: list[DocumentBlock] = []
    buffer_section: str = ""
    passage_counter = 0
    skipped_short = 0
    split_long = 0
    sections_found: set[str] = set()
    total_blocks = len(document.blocks)

    def flush_buffer() -> None:
        nonlocal passage_counter, skipped_short, split_long
        if not buffer_blocks:
            return
        text = " ".join(b.text.strip() for b in buffer_blocks if b.text.strip())
        if not text:
            buffer_blocks.clear()
            return
        if len(text) < cfg.min_passage_chars:
            if _should_keep_short_passage(buffer_section, buffer_blocks, text):
                passage_counter += 1
                passages.append(_make_passage(paper_id, f"p{passage_counter:03d}", buffer_section, buffer_blocks, text))
                buffer_blocks.clear()
                return
            skipped_short += 1
            warnings.append(
                WarningItem(
                    code="SHORT_PASSAGE_SKIPPED",
                    message=f"Passage too short ({len(text)} chars < {cfg.min_passage_chars}), skipped.",
                )
            )
            buffer_blocks.clear()
            return
        if len(text) <= cfg.max_passage_chars:
            passage_counter += 1
            passages.append(_make_passage(paper_id, f"p{passage_counter:03d}", buffer_section, buffer_blocks, text))
        else:
            chunks = _split_text(text, cfg.max_passage_chars)
            split_long += len(chunks) - 1
            for chunk in chunks:
                if len(chunk.strip()) < cfg.min_passage_chars:
                    skipped_short += 1
                    continue
                passage_counter += 1
                passages.append(_make_passage(paper_id, f"p{passage_counter:03d}", buffer_section, buffer_blocks, chunk.strip()))
        buffer_blocks.clear()

    def flush_standalone(block: DocumentBlock) -> None:
        nonlocal passage_counter
        text = _standalone_text(block)
        if not text:
            return
        section = _normalize_section(block.section) or "unknown"
        sections_found.add(section)
        passage_counter += 1
        passages.append(_make_passage(paper_id, f"p{passage_counter:03d}", section, [block], text))

    for block in document.blocks:
        # Heading / title: section boundary only
        if block.type in (BlockType.HEADING, BlockType.TITLE):
            flush_buffer()
            buffer_section = _normalize_section(block.section)
            if buffer_section:
                sections_found.add(buffer_section)
            continue

        # Formula: standalone passage
        if cfg.formula_standalone and block.type == BlockType.FORMULA:
            flush_buffer()
            flush_standalone(block)
            continue

        # Table: standalone passage
        if cfg.table_standalone and block.type == BlockType.TABLE:
            flush_buffer()
            flush_standalone(block)
            continue

        # Empty text: skip
        if not block.text.strip():
            continue

        # Section change: flush buffer
        block_section = _normalize_section(block.section)
        if block_section and block_section != buffer_section and buffer_blocks:
            flush_buffer()
            buffer_section = block_section
        if block_section:
            sections_found.add(block_section)
            # A title/heading can leave a section label behind even though it
            # contributes no buffered text. The first real paragraph owns its
            # declared section and must not inherit that stale label.
            if not buffer_blocks:
                buffer_section = block_section

        buffer_blocks.append(block)

    # Flush remaining
    flush_buffer()

    # If no passages, add warning
    if not passages:
        warnings.append(
            WarningItem(code="NO_PASSAGES", message="No passages could be extracted from the document.")
        )

    return PassageIndex(
        paper_id=paper_id,
        passages=passages,
        warnings=warnings,
        build_config=cfg,
        stats=PassageIndexStats(
            total_passages=len(passages),
            total_blocks=total_blocks,
            skipped_short=skipped_short,
            split_long=split_long,
            sections_found=sorted(sections_found),
        ),
    )


def _make_passage(
    paper_id: str,
    passage_id: str,
    section: str,
    blocks: list[DocumentBlock],
    text: str,
) -> Passage:
    pages = [b.page for b in blocks if b.page is not None]
    formula_pages = [b.formula_page for b in blocks if b.formula_page is not None]
    risk_flags: list[str] = []
    for block in blocks:
        for flag in block.risk_flags:
            if flag not in risk_flags:
                risk_flags.append(flag)
    return Passage(
        passage_id=passage_id,
        paper_id=paper_id,
        block_ids=[b.block_id for b in blocks],
        section=section or "unknown",
        text=text,
        normalized_text=" ".join(text.lower().split()),
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
        token_count=len(text.split()),
        evidence_refs=[b.evidence_ref for b in blocks if b.evidence_ref],
        source_block_types=[b.type.value for b in blocks],
        formula_ids=[b.formula_id for b in blocks if b.formula_id],
        formula_origins=[b.formula_origin for b in blocks if b.formula_origin],
        formula_pages=formula_pages,
        formula_ocr_statuses=[b.formula_ocr_status for b in blocks if b.formula_ocr_status],
        block_sources=[b.block_source for b in blocks if b.block_source],
        risk_flags=risk_flags,
    )


def _normalize_section(section: str) -> str:
    return section.strip().lower().replace(" ", "_") if section else ""


def _standalone_text(block: DocumentBlock) -> str:
    text = block.text.strip()
    if block.type != BlockType.FORMULA:
        return text
    before = " ".join(block.formula_context_before.split()).strip()
    after = " ".join(block.formula_context_after.split()).strip()
    if not before and not after:
        return text
    formula_id = block.formula_id or block.block_id
    origin = block.formula_origin or "unknown"
    return "\n".join(
        [
            f"Formula {formula_id}. Origin: {origin}.",
            f"Formula: {text}",
            f"Context before: {before or 'unknown'}",
            f"Context after: {after or 'unknown'}",
        ]
    )


def _should_keep_short_passage(section: str, blocks: list[DocumentBlock], text: str) -> bool:
    normalized_section = _normalize_section(section)
    if normalized_section not in SHORT_EVIDENCE_SECTIONS:
        return False
    if not any(block.evidence_ref for block in blocks):
        return False
    return bool(SHORT_EVIDENCE_KEYWORDS.search(text))


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text at sentence boundaries, respecting max_chars."""
    sentences = SENTENCE_SPLIT.split(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current:
        chunks.append(current)
    return chunks
