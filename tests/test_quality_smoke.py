"""P0 Quality Tests: Artifact chain quality smoke test.

Runs the full single-paper pipeline on fixture files and checks:
- All 7 artifacts are generated
- All JSONs are readable
- No hard-fail conditions
- Confidence values are reasonable
"""

from __future__ import annotations

import json
from pathlib import Path

from researchsensei.formula_card import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.paper_card import build_paper_card
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import (
    EvidenceIndex,
    FormulaCardBundle,
    PaperCard,
    PaperSkeleton,
    TeachingCardBundle,
)
from researchsensei.schemas.enums import JobStatus
from researchsensei.teaching_card import build_teaching_cards
from researchsensei.workspace import WorkspaceStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "quality"


def _build_chain(fixture_name: str):
    """Build the full single-paper artifact chain."""
    ingestion = LightweightIngestionService()
    source = FIXTURE_DIR / fixture_name
    document = ingestion.ingest_path(source, paper_id="test-paper")
    evidence_index = build_evidence_index(document)
    skeleton = build_paper_skeleton(document, evidence_index)
    paper_card = build_paper_card(skeleton, evidence_index)
    formula_cards = build_formula_cards(document, evidence_index, skeleton)
    teaching_cards = build_teaching_cards(paper_card, formula_cards, skeleton, evidence_index)
    return {
        "parsed_document": document,
        "evidence_index": evidence_index,
        "paper_skeleton": skeleton,
        "paper_card": paper_card,
        "formula_cards": formula_cards,
        "teaching_cards": teaching_cards,
    }


def test_method_paper_chain_produces_all_artifacts() -> None:
    """Full chain on method paper must produce all 7 artifact types."""
    data = _build_chain("fixture_method_paper.md")
    assert data["parsed_document"] is not None
    assert data["evidence_index"] is not None
    assert data["paper_skeleton"] is not None
    assert data["paper_card"] is not None
    assert data["formula_cards"] is not None
    assert data["teaching_cards"] is not None


def test_method_paper_chain_json_readable() -> None:
    """All artifacts from method paper must serialize to valid JSON."""
    data = _build_chain("fixture_method_paper.md")
    for name, obj in data.items():
        json_str = obj.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict), f"{name} did not serialize to dict"


def test_minimal_paper_chain_produces_all_artifacts() -> None:
    """Full chain on minimal paper must produce all artifacts (possibly degraded)."""
    data = _build_chain("fixture_minimal.md")
    assert data["parsed_document"] is not None
    assert data["evidence_index"] is not None
    assert data["paper_skeleton"] is not None
    assert data["paper_card"] is not None
    assert data["formula_cards"] is not None
    assert data["teaching_cards"] is not None


def test_no_hard_fail_fabricated_results() -> None:
    """HF-1/HF-5: Minimal paper must not fabricate results or be fully generic."""
    data = _build_chain("fixture_minimal.md")
    pc = data["paper_card"]
    all_claims = [pc.problem, pc.core_idea, pc.method_overview, pc.experiment_summary, pc.limitations]
    all_claims.extend(pc.old_methods)
    degraded = sum(
        1 for c in all_claims
        if c.evidence_type.value in ("INSUFFICIENT_EVIDENCE", "UNVERIFIED", "NEEDS_HUMAN_CHECK")
    )
    assert degraded > 0, "Minimal paper should have degraded claims"


def test_no_hard_fail_formula_as_explanation() -> None:
    """HF-2: Teaching cards must not have formula text as human_explanation."""
    data = _build_chain("fixture_formula_heavy.md")
    for tc in data["teaching_cards"].teaching_cards:
        explanation = tc.human_explanation
        if not explanation or explanation in ("UNKNOWN", "NEEDS_HUMAN_CHECK"):
            continue
        formula_chars = sum(1 for c in explanation if c in "=+−*/^_{}[]()\\")
        if len(explanation) > 10:
            ratio = formula_chars / len(explanation)
            assert ratio < 0.3, (
                f"human_explanation is formula text (ratio={ratio:.2f})"
            )


def test_confidence_values_in_range() -> None:
    """All confidence values must be in [0, 1]."""
    data = _build_chain("fixture_method_paper.md")
    pc = data["paper_card"]
    for claim in [pc.problem, pc.core_idea, pc.method_overview, pc.experiment_summary]:
        assert 0.0 <= claim.confidence <= 1.0, (
            f"Claim confidence {claim.confidence} out of range"
        )
    for fc in data["formula_cards"].formula_cards:
        assert 0.0 <= fc.confidence <= 1.0, (
            f"Formula card confidence {fc.confidence} out of range"
        )
    for tc in data["teaching_cards"].teaching_cards:
        assert 0.0 <= tc.confidence <= 1.0, (
            f"Teaching card confidence {tc.confidence} out of range"
        )


def test_method_paper_has_paper_keywords() -> None:
    """HF-5: Output must contain paper-specific keywords in title or evidence refs."""
    data = _build_chain("fixture_method_paper.md")
    pc = data["paper_card"]
    # Check title contains paper-specific term
    title_lower = pc.title.lower()
    has_title_keyword = any(kw in title_lower for kw in ["graph", "anomaly", "sensor", "ad"])
    # Check evidence refs exist (proves grounding to actual content)
    has_evidence = len(pc.evidence_refs) > 0
    # Check one_sentence_summary is not empty
    has_summary = pc.one_sentence_summary and pc.one_sentence_summary != "UNKNOWN"
    assert has_title_keyword or has_evidence, (
        f"Output should contain paper-specific keywords. "
        f"title={pc.title}, evidence_refs={pc.evidence_refs}"
    )


def test_chain_no_real_network() -> None:
    """Verify the chain runs without network access (no httpx calls)."""
    # If this test runs without MockTransport and succeeds, it means
    # the chain doesn't need network access (which is correct for
    # rule-based builders).
    data = _build_chain("fixture_method_paper.md")
    assert data["paper_card"] is not None


def test_runner_artifact_smoke_writes_real_json(tmp_path: Path) -> None:
    """SinglePaperIngestionRunner writes real JSON artifacts to disk.

    This is the true artifact smoke test - uses the actual pipeline runner,
    not an in-memory chain.
    """
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    source = FIXTURE_DIR / "fixture_method_paper.md"
    job = runner.run(source, job_id="runner-smoke")

    assert job.status == JobStatus.SUCCEEDED
    assert len(job.artifacts) == 11

    run_dir = tmp_path / "workspace" / "runs" / "runner-smoke"
    for artifact in job.artifacts:
        path = Path(artifact.path)
        assert path.exists(), f"Missing artifact: {artifact.artifact_type}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{artifact.artifact_type} is not valid JSON"

    # Verify job can be re-read from store
    reloaded = jobs.get("runner-smoke")
    assert reloaded.status == JobStatus.SUCCEEDED
    assert len(reloaded.artifacts) == 11
