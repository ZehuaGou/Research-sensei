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

    def flush_as_split_passages(blocks: list[DocumentBlock], section: str) -> None:
        nonlocal passage_counter, split_long
        text = " ".join(b.text.strip() for b in blocks if b.text.strip())
        if not text:
            return
        if len(text) <= cfg.max_passage_chars:
            passage_counter += 1
            passages.append(_make_passage(paper_id, f"p{passage_counter:03d}", section, blocks, text))
            return
        # Split at sentence boundaries
        chunks = _split_text(text, cfg.max_passage_chars)
        split_long += len(chunks) - 1
        for chunk in chunks:
            if len(chunk.strip()) < cfg.min_passage_chars:
                skipped_short += 1
                continue
            passage_counter += 1
            passages.append(
                _make_passage(paper_id, f"p{passage_counter:03d}", section, blocks, chunk.strip())
            )

    def flush_standalone(block: DocumentBlock) -> None:
        nonlocal passage_counter
        text = block.text.strip()
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
            if not buffer_section:
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
    )


def _normalize_section(section: str) -> str:
    return section.strip().lower().replace(" ", "_") if section else ""


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
