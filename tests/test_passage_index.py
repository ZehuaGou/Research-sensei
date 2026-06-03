from __future__ import annotations

import json
from pathlib import Path

from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import (
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    JobStatus,
    Passage,
    PassageIndex,
    PassageIndexBuildConfig,
    WarningItem,
)
from researchsensei.workspace import WorkspaceStore


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_passage_json_round_trip() -> None:
    passage = Passage(
        passage_id="p001",
        paper_id="test",
        block_ids=["b001", "b002"],
        section="method",
        text="We propose a model.",
        normalized_text="we propose a model.",
        token_count=4,
        evidence_refs=["test:b001", "test:b002"],
        source_block_types=["paragraph", "paragraph"],
    )

    json_str = passage.model_dump_json()
    restored = Passage.model_validate_json(json_str)

    assert restored.passage_id == "p001"
    assert restored.paper_id == "test"
    assert restored.block_ids == ["b001", "b002"]
    assert restored.section == "method"
    assert restored.text == "We propose a model."
    assert restored.token_count == 4
    assert restored.evidence_refs == ["test:b001", "test:b002"]


def test_passage_index_json_round_trip() -> None:
    passage = Passage(passage_id="p001", paper_id="test", text="Hello world")
    index = PassageIndex(
        paper_id="test",
        passages=[passage],
        warnings=[WarningItem(code="TEST", message="test warning")],
    )

    json_str = index.model_dump_json()
    restored = PassageIndex.model_validate_json(json_str)

    assert restored.schema_version == "v2"
    assert restored.paper_id == "test"
    assert len(restored.passages) == 1
    assert restored.passages[0].passage_id == "p001"
    assert len(restored.warnings) == 1
    assert restored.warnings[0].code == "TEST"


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------


def _make_document(blocks: list[DocumentBlock], paper_id: str = "test") -> DocumentIngestion:
    return DocumentIngestion(paper_id=paper_id, blocks=blocks)


def test_heading_becomes_section_boundary() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="We propose a new approach for anomaly detection in time series data.", evidence_ref="t:b001", section="method"),
    ])

    index = build_passage_index(doc)

    assert len(index.passages) == 1
    assert index.passages[0].section == "method"
    assert "h001" not in index.passages[0].block_ids
    assert "b001" in index.passages[0].block_ids


def test_same_section_paragraphs_merge() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="We propose a new approach for anomaly detection in time series data.", evidence_ref="t:b001", section="method"),
        DocumentBlock(block_id="b002", type=BlockType.PARAGRAPH, text="Our model uses graph neural networks to capture sensor dependencies.", evidence_ref="t:b002", section="method"),
    ])

    index = build_passage_index(doc)

    assert len(index.passages) == 1
    assert "b001" in index.passages[0].block_ids
    assert "b002" in index.passages[0].block_ids
    assert "We propose" in index.passages[0].text
    assert "graph neural" in index.passages[0].text


def test_formula_block_standalone_passage() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="We optimize the following objective function for training.", evidence_ref="t:b001", section="method"),
        DocumentBlock(block_id="eq001", type=BlockType.FORMULA, text="L = L_rec + lambda * L_reg", evidence_ref="t:eq001", section="method", raw_latex="L = L_rec + \\lambda L_{reg}"),
        DocumentBlock(block_id="b002", type=BlockType.PARAGRAPH, text="The first term is reconstruction loss and the second is regularization.", evidence_ref="t:b002", section="method"),
    ])

    index = build_passage_index(doc)

    formula_passages = [p for p in index.passages if "eq001" in p.block_ids]
    assert len(formula_passages) == 1
    assert len(formula_passages[0].block_ids) == 1
    assert formula_passages[0].text == "L = L_rec + lambda * L_reg"


def test_table_block_standalone_passage() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Results", evidence_ref="t:h001", section="experiments"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="Table 1 shows the comparison results across all baselines.", evidence_ref="t:b001", section="experiments"),
        DocumentBlock(block_id="tab001", type=BlockType.TABLE, text="Model | F1 | Acc\nOurs | 95.2 | 97.1", evidence_ref="t:tab001", section="experiments"),
    ])

    index = build_passage_index(doc)

    table_passages = [p for p in index.passages if "tab001" in p.block_ids]
    assert len(table_passages) == 1
    assert len(table_passages[0].block_ids) == 1


def test_missing_section_becomes_unknown() -> None:
    doc = _make_document([
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="Some text without a clear section header for processing.", evidence_ref="t:b001", section=""),
    ])

    index = build_passage_index(doc)

    assert len(index.passages) == 1
    assert index.passages[0].section == "unknown"


def test_evidence_refs_preserved() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="We propose a new method for solving this problem effectively.", evidence_ref="t:b001", section="method"),
        DocumentBlock(block_id="b002", type=BlockType.PARAGRAPH, text="Our approach builds on prior work in graph neural networks.", evidence_ref="t:b002", section="method"),
    ])

    index = build_passage_index(doc)

    assert len(index.passages) == 1
    assert "t:b001" in index.passages[0].evidence_refs
    assert "t:b002" in index.passages[0].evidence_refs


def test_passage_ids_sequential() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Abstract", evidence_ref="t:h001", section="abstract"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="We study anomaly detection in multivariate time series data.", evidence_ref="t:b001", section="abstract"),
        DocumentBlock(block_id="h002", type=BlockType.HEADING, text="Method", evidence_ref="t:h002", section="method"),
        DocumentBlock(block_id="b002", type=BlockType.PARAGRAPH, text="We propose a graph-based approach for modeling sensor dependencies.", evidence_ref="t:b002", section="method"),
    ])

    index = build_passage_index(doc)

    ids = [p.passage_id for p in index.passages]
    assert ids == ["p001", "p002"]


def test_short_passage_skipped_with_warning() -> None:
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text="Short.", evidence_ref="t:b001", section="method"),
    ])

    index = build_passage_index(doc)

    assert len(index.passages) == 0
    assert any(w.code == "SHORT_PASSAGE_SKIPPED" for w in index.warnings)
    assert index.stats is not None
    assert index.stats.skipped_short == 1


def test_long_passage_split_updates_stats() -> None:
    long_text = "This is a sentence. " * 200  # ~4000 chars
    doc = _make_document([
        DocumentBlock(block_id="h001", type=BlockType.HEADING, text="Method", evidence_ref="t:h001", section="method"),
        DocumentBlock(block_id="b001", type=BlockType.PARAGRAPH, text=long_text, evidence_ref="t:b001", section="method"),
    ])

    index = build_passage_index(doc, config=PassageIndexBuildConfig(max_passage_chars=1000))

    assert len(index.passages) > 1
    assert index.stats is not None
    assert index.stats.split_long > 0


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


def _write_sample_md(tmp_path: Path) -> Path:
    path = tmp_path / "paper.md"
    path.write_text(
        "# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe propose a model.\n\n## Experiments\nTable 1 reports F1.",
        encoding="utf-8",
    )
    return path


def test_runner_writes_passage_index_artifact(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-pi")

    passage_index_path = tmp_path / "workspace" / "runs" / "test-pi" / "passage_index.json"
    assert passage_index_path.exists()
    data = json.loads(passage_index_path.read_text(encoding="utf-8"))
    assert data["paper_id"] == "test-pi"
    assert "passages" in data


def test_runner_existing_evidence_index_still_exists(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-ei")

    evidence_path = tmp_path / "workspace" / "runs" / "test-ei" / "evidence_index.json"
    assert evidence_path.exists()
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert "claims" in data


def test_runner_artifact_count_includes_passage_index(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-count")

    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "passage_index" in artifact_types
    assert len(job.artifacts) == 10
    expected = {
        "source_status", "ingestion", "passage_index", "claim_evidence", "evidence_index",
        "paper_skeleton", "paper_card", "formula_cards", "teaching_cards", "understanding_status",
    }
    assert artifact_types == expected


def test_runner_card_artifacts_unchanged(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-cards")

    run_dir = tmp_path / "workspace" / "runs" / "test-cards"
    card_path = run_dir / "paper_card.json"
    formula_path = run_dir / "formula_cards.json"
    teaching_path = run_dir / "teaching_cards.json"
    assert card_path.exists()
    assert formula_path.exists()
    assert teaching_path.exists()
    card_data = json.loads(card_path.read_text(encoding="utf-8"))
    assert "paper_id" in card_data
