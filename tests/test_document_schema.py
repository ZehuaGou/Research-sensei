from __future__ import annotations

import json

from researchsensei.schemas import BlockType, DocumentBlock, DocumentIngestion, ParseMetadata, ParserResult


def test_parse_metadata_defaults() -> None:
    meta = ParseMetadata(parser_name="test")

    assert meta.parser_name == "test"
    assert meta.parser_version == ""
    assert meta.source_format == ""
    assert meta.page_count == 0
    assert meta.extra == {}


def test_parser_result_json_round_trip() -> None:
    doc = DocumentIngestion(paper_id="p1", blocks=[])
    meta = ParseMetadata(parser_name="lightweight", source_format="md")
    result = ParserResult(document=doc, metadata=meta)

    json_str = result.model_dump_json()
    restored = ParserResult.model_validate_json(json_str)

    assert restored.document.paper_id == "p1"
    assert restored.metadata.parser_name == "lightweight"
    assert restored.metadata.source_format == "md"


def test_document_block_new_fields_round_trip() -> None:
    block = DocumentBlock(
        block_id="b001",
        type=BlockType.TABLE,
        text="Table content",
        evidence_ref="p1:b001",
        bbox=(0.1, 0.2, 0.8, 0.9),
        table_html="<table><tr><td>x</td></tr></table>",
        figure_caption="Fig 1: Overview",
        reference_entries=["[1] Smith 2020", "[2] Jones 2021"],
    )

    json_str = block.model_dump_json()
    restored = DocumentBlock.model_validate_json(json_str)

    assert restored.bbox == (0.1, 0.2, 0.8, 0.9)
    assert restored.table_html == "<table><tr><td>x</td></tr></table>"
    assert restored.figure_caption == "Fig 1: Overview"
    assert restored.reference_entries == ["[1] Smith 2020", "[2] Jones 2021"]


def test_document_block_new_fields_backward_compatible() -> None:
    old_json = json.dumps({
        "block_id": "b001",
        "type": "paragraph",
        "text": "Some text",
        "evidence_ref": "p1:b001",
    })

    block = DocumentBlock.model_validate_json(old_json)

    assert block.block_id == "b001"
    assert block.text == "Some text"
    assert block.bbox is None
    assert block.table_html == ""
    assert block.figure_caption == ""
    assert block.reference_entries == []
