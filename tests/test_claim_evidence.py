from __future__ import annotations

import json
from pathlib import Path

from researchsensei.evidence.claim_extractor import build_claim_evidence
from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import (
    BlockType,
    ClaimEvidence,
    ClaimEvidenceBundle,
    ClaimEvidenceRecord,
    DocumentBlock,
    DocumentIngestion,
    EvidenceIndex,
    EvidenceType,
    JobStatus,
    Passage,
    PassageIndex,
)
from researchsensei.workspace import WorkspaceStore


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_claim_evidence_record_round_trip() -> None:
    claim = ClaimEvidenceRecord(
        claim_id="p1:claim:c001",
        claim_text="We propose a new method.",
        evidence_ref="p1:b001",
        block_id="b001",
        passage_id="p001",
        section="method",
        claim_type="METHOD",
        semantic_support="DIRECT_QUOTE",
        source_sentence="We propose a new method.",
        quote_or_summary="We propose a new method.",
        confidence=0.7,
        generated_by="rule",
    )

    json_str = claim.model_dump_json()
    restored = ClaimEvidenceRecord.model_validate_json(json_str)

    assert restored.claim_id == "p1:claim:c001"
    assert restored.claim_type == "METHOD"
    assert restored.passage_id == "p001"
    assert restored.generated_by == "rule"
    assert restored.confidence == 0.7


def test_claim_evidence_bundle_round_trip() -> None:
    claim = ClaimEvidenceRecord(
        claim_id="p1:claim:c001",
        claim_text="Test claim.",
        evidence_ref="p1:b001",
        block_id="b001",
        passage_id="p001",
        confidence=0.5,
    )
    bundle = ClaimEvidenceBundle(
        paper_id="p1",
        claims=[claim],
        source_artifacts=["passage_index.json"],
    )

    json_str = bundle.model_dump_json()
    restored = ClaimEvidenceBundle.model_validate_json(json_str)

    assert restored.schema_version == "claim_evidence"
    assert restored.paper_id == "p1"
    assert len(restored.claims) == 1
    assert restored.claims[0].claim_id == "p1:claim:c001"
    assert restored.source_artifacts == ["passage_index.json"]


def test_claim_evidence_v1_unchanged() -> None:
    """ClaimEvidence v1 should still work exactly as before."""
    claim = ClaimEvidence(
        claim_id="p1-title-b001",
        claim_text="This block is a title candidate.",
        evidence_type=EvidenceType.SUPPORTED_BY_TEXT,
        evidence_ref="p1:b001",
        block_id="b001",
        section="title",
        quote_or_summary="Paper Title",
        confidence=0.75,
    )

    assert claim.claim_id == "p1-title-b001"
    assert claim.evidence_type == EvidenceType.SUPPORTED_BY_TEXT
    assert claim.block_id == "b001"


def test_evidence_index_v1_still_loads() -> None:
    """EvidenceIndex v1 should still load correctly."""
    index = EvidenceIndex(
        paper_id="p1",
        claims=[
            ClaimEvidence(
                claim_id="p1-title-b001",
                claim_text="title",
                evidence_type=EvidenceType.SUPPORTED_BY_TEXT,
                evidence_ref="p1:b001",
                block_id="b001",
                section="title",
                quote_or_summary="Title",
                confidence=0.75,
            )
        ],
        warnings=["FORMULA_UNAVAILABLE"],
    )

    json_str = index.model_dump_json()
    restored = EvidenceIndex.model_validate_json(json_str)

    assert restored.paper_id == "p1"
    assert len(restored.claims) == 1
    assert restored.warnings == ["FORMULA_UNAVAILABLE"]


# ---------------------------------------------------------------------------
# ClaimExtractor tests
# ---------------------------------------------------------------------------


def _make_passage(
    passage_id: str,
    section: str,
    text: str,
    block_ids: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    source_block_types: list[str] | None = None,
) -> Passage:
    return Passage(
        passage_id=passage_id,
        paper_id="test",
        block_ids=block_ids or [f"b{passage_id[1:]}"],
        section=section,
        text=text,
        normalized_text=text.lower(),
        token_count=len(text.split()),
        evidence_refs=evidence_refs or [f"test:b{passage_id[1:]}"],
        source_block_types=source_block_types or ["paragraph"],
    )


def _make_document(paper_id: str = "test") -> DocumentIngestion:
    return DocumentIngestion(paper_id=paper_id, blocks=[])


def test_method_claim_from_method_section() -> None:
    passage = _make_passage("p001", "method", "We propose a graph neural network for anomaly detection.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "METHOD"
    assert bundle.claims[0].passage_id == "p001"
    assert bundle.claims[0].semantic_support == "DIRECT_QUOTE"
    assert "propose" in bundle.claims[0].source_sentence.lower()


def test_method_claim_fallback_paraphrase_when_no_keywords() -> None:
    passage = _make_passage("p001", "method", "The sensor data is processed through multiple layers of computation.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "METHOD"
    assert bundle.claims[0].semantic_support == "PARAPHRASE"


def test_result_claim_from_experiment_section() -> None:
    passage = _make_passage("p001", "experiments", "Our model achieves 95.2 F1 score on the benchmark.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "RESULT"
    assert bundle.claims[0].semantic_support == "DIRECT_QUOTE"
    assert "achieves" in bundle.claims[0].source_sentence.lower()


def test_formula_claim_from_formula_passage() -> None:
    passage = _make_passage(
        "p001", "method", "L = L_rec + lambda * L_reg",
        source_block_types=["formula"],
    )
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "FORMULA_CONTEXT"


def test_contribution_claim_from_abstract() -> None:
    passage = _make_passage("p001", "abstract", "We propose a novel approach to anomaly detection in time series.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "CONTRIBUTION"
    assert "propose" in bundle.claims[0].source_sentence.lower()


def test_definition_claim_from_definition_text() -> None:
    passage = _make_passage("p001", "background", "Anomaly is defined as a deviation from normal behavior.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "DEFINITION"


def test_problem_claim_from_introduction() -> None:
    passage = _make_passage("p001", "introduction", "Detecting anomalies in multivariate time series is a challenging problem.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert len(bundle.claims) == 1
    assert bundle.claims[0].claim_type == "PROBLEM"


def test_no_template_claims_generated() -> None:
    """Claims should never be template sentences like 'This block belongs to...'."""
    passage = _make_passage("p001", "method", "We propose a new model for time series analysis.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    for claim in bundle.claims:
        assert "This block belongs to" not in claim.claim_text
        assert "This block is a" not in claim.claim_text


def test_claim_id_format_stable() -> None:
    passage = _make_passage("p001", "method", "We propose a graph-based approach for anomaly detection.")
    index = PassageIndex(paper_id="test-paper", passages=[passage])
    doc = _make_document("test-paper")

    bundle = build_claim_evidence(doc, index)

    assert bundle.claims[0].claim_id == "test-paper:claim:c001"


def test_passage_id_exists_in_passage_index() -> None:
    passage = _make_passage("p001", "method", "We propose a new approach for anomaly detection.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    passage_ids = {p.passage_id for p in index.passages}
    for claim in bundle.claims:
        assert claim.passage_id in passage_ids


def test_evidence_ref_preserved_from_passage() -> None:
    passage = _make_passage(
        "p001", "method", "We propose a new method.",
        evidence_refs=["test:b001", "test:b002"],
    )
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    assert bundle.claims[0].evidence_ref == "test:b001"


def test_no_claims_warning() -> None:
    """Empty passages should produce NO_CLAIMS warning."""
    passage = _make_passage("p001", "full_text", "Some random text without any structure.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    if not bundle.claims:
        assert any(w.code == "NO_CLAIMS" for w in bundle.warnings)


def test_generated_by_is_rule() -> None:
    passage = _make_passage("p001", "method", "We propose a new model for anomaly detection.")
    index = PassageIndex(paper_id="test", passages=[passage])
    doc = _make_document()

    bundle = build_claim_evidence(doc, index)

    for claim in bundle.claims:
        assert claim.generated_by == "rule"


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


def test_runner_writes_claim_evidence_artifact(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-ce")

    claim_evidence_path = tmp_path / "workspace" / "runs" / "test-ce" / "claim_evidence.json"
    assert claim_evidence_path.exists()
    data = json.loads(claim_evidence_path.read_text(encoding="utf-8"))
    assert data["paper_id"] == "test-ce"
    assert data["schema_version"] == "claim_evidence"
    assert "claims" in data


def test_runner_artifact_count_includes_claim_evidence(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-count")

    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "claim_evidence" in artifact_types
    assert len(job.artifacts) == 11
    expected = {
        "source_status", "ingestion", "passage_index", "claim_evidence",
        "evidence_index", "paper_skeleton", "paper_card", "formula_cards", "teaching_cards", "understanding_status",
        "quality_report",
    }
    assert artifact_types == expected


def test_runner_evidence_index_still_exists(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-ei")

    evidence_path = tmp_path / "workspace" / "runs" / "test-ei" / "evidence_index.json"
    assert evidence_path.exists()
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert "claims" in data


def test_runner_card_artifacts_unchanged(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-cards")

    run_dir = tmp_path / "workspace" / "runs" / "test-cards"
    assert (run_dir / "paper_card.json").exists()
    assert (run_dir / "formula_cards.json").exists()
    assert (run_dir / "teaching_cards.json").exists()
    card_data = json.loads((run_dir / "paper_card.json").read_text(encoding="utf-8"))
    assert "paper_id" in card_data


def test_runner_claim_evidence_does_not_change_old_card_outputs(tmp_path: Path) -> None:
    """Claim evidence artifact should not affect paper_card / formula_cards / teaching_cards."""
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-unchanged")

    run_dir = tmp_path / "workspace" / "runs" / "test-unchanged"
    card_data = json.loads((run_dir / "paper_card.json").read_text(encoding="utf-8"))
    formula_data = json.loads((run_dir / "formula_cards.json").read_text(encoding="utf-8"))
    teaching_data = json.loads((run_dir / "teaching_cards.json").read_text(encoding="utf-8"))

    assert card_data["paper_id"] == "test-unchanged"
    assert "formula_cards" in formula_data
    assert "teaching_cards" in teaching_data
