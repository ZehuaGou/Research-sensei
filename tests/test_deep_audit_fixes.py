"""Deep audit fix tests.

Covers the 7 issues found in Pre-Phase12 deep audit.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from researchsensei.direction import DirectionRunner
from researchsensei.formula_card import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.llm.client import LLMClient, MockLLMClient
from researchsensei.llm.types import ChatMessage, LLMConfig
from researchsensei.query.planner import QueryPlanner, QueryPlanningError
from researchsensei.schemas import CandidatePaper, QueryPlan
from researchsensei.schemas.enums import EvidenceType, JobStatus
from researchsensei.selection import SelectionService
from researchsensei.workspace import WorkspaceStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "quality"


# ---------------------------------------------------------------------------
# Test 1: LLMClient.chat(config=...) affects payload
# ---------------------------------------------------------------------------

def test_llm_client_config_affects_payload() -> None:
    """Passing config to chat() must override temperature/max_tokens in payload."""
    from researchsensei.core.config import ModelProviderConfig

    provider = ModelProviderConfig(
        name="test-provider",
        base_url="https://api.example.com/v1",
        model="test-model",
        api_key_env="TEST_KEY",
    )
    client = LLMClient(provider)

    default_config = LLMConfig(temperature=0.7, max_tokens=100)
    override_config = LLMConfig(temperature=0.3, max_tokens=500)

    messages = [ChatMessage(role="user", content="test")]

    # Default payload
    payload_default = client._chat_payload(messages, config=default_config)
    assert payload_default["temperature"] == 0.7
    assert payload_default["max_tokens"] == 100

    # Override payload
    payload_override = client._chat_payload(messages, config=override_config)
    assert payload_override["temperature"] == 0.3
    assert payload_override["max_tokens"] == 500


# ---------------------------------------------------------------------------
# Test 2: SinglePaperIngestionRunner marks job FAILED on exception
# ---------------------------------------------------------------------------

def test_runner_marks_job_failed_on_card_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If card building raises, job must be marked FAILED with WarningItem."""
    from researchsensei.schemas.common import WarningItem

    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    source = tmp_path / "test.md"
    source.write_text("# Test Paper\n\n## Abstract\nThis is a test.\n", encoding="utf-8")

    # Monkeypatch build_paper_card to raise
    def _fail_build_paper_card(*args, **kwargs):
        raise RuntimeError("Simulated card build failure")

    monkeypatch.setattr(
        "researchsensei.ingestion.pipeline.build_paper_card",
        _fail_build_paper_card,
    )

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)
    job = runner.run(source, job_id="fail-job")

    # Must be FAILED
    assert job.status == JobStatus.FAILED
    assert job.current_step == "pipeline_error"
    assert "Simulated card build failure" in job.error

    # Must have WarningItem, not str
    assert len(job.warnings) > 0
    assert isinstance(job.warnings[0], WarningItem)
    assert job.warnings[0].code == "PIPELINE_FAILED"

    # Must be re-readable from store
    reloaded = jobs.get("fail-job")
    assert reloaded.status == JobStatus.FAILED
    assert isinstance(reloaded.warnings[0], WarningItem)

    # Must NOT have written card artifacts
    run_dir = tmp_path / "workspace" / "runs" / "fail-job"
    assert not (run_dir / "paper_card.json").exists()
    assert not (run_dir / "formula_cards.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()


# ---------------------------------------------------------------------------
# Test 3: Real artifact smoke uses SinglePaperIngestionRunner
# ---------------------------------------------------------------------------

def test_real_artifact_smoke_uses_single_paper_runner(tmp_path: Path) -> None:
    """Smoke test: full pipeline via SinglePaperIngestionRunner produces all 7 artifacts."""
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    source = FIXTURE_DIR / "fixture_method_paper.md"
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)
    job = runner.run(source, job_id="smoke-test")

    assert job.status == JobStatus.SUCCEEDED

    run_dir = tmp_path / "workspace" / "runs" / "smoke-test"
    expected_artifacts = [
        "source_status.json",
        "parsed_document.json",
        "evidence_index.json",
        "paper_skeleton.json",
        "paper_card.json",
        "formula_cards.json",
        "teaching_cards.json",
    ]
    for artifact in expected_artifacts:
        path = run_dir / artifact
        assert path.exists(), f"Missing artifact: {artifact}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{artifact} is not a valid JSON dict"


# ---------------------------------------------------------------------------
# Test 4: Formula symbol generic meaning is REASONABLE_INFERENCE
# ---------------------------------------------------------------------------

def test_formula_symbol_generic_meaning_is_not_supported_by_formula() -> None:
    """Symbols from generic dictionary should be REASONABLE_INFERENCE, not SUPPORTED_BY_FORMULA."""
    ingestion = LightweightIngestionService()
    source = FIXTURE_DIR / "fixture_formula_heavy.md"
    document = ingestion.ingest_path(source, paper_id="test-paper")
    evidence_index = build_evidence_index(document)

    from researchsensei.paper_skeleton import build_paper_skeleton
    skeleton = build_paper_skeleton(document, evidence_index)
    formula_cards = build_formula_cards(document, evidence_index, skeleton)

    for fc in formula_cards.formula_cards:
        for sym in fc.symbols:
            if sym.meaning != "UNKNOWN":
                # Generic dictionary meanings should be REASONABLE_INFERENCE
                assert sym.evidence_status == EvidenceType.REASONABLE_INFERENCE, (
                    f"Symbol '{sym.symbol}' meaning '{sym.meaning}' has "
                    f"evidence_status={sym.evidence_status}, expected REASONABLE_INFERENCE"
                )


# ---------------------------------------------------------------------------
# Test 5: DirectionRunner records adapter failure in warnings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_direction_runner_records_adapter_failure_warning(tmp_path: Path) -> None:
    """When an adapter fails, the failure must appear in bundle warnings."""
    workspace = WorkspaceStore(tmp_path / "workspace")

    class _FailingAdapter:
        def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
            raise RuntimeError("Connection refused")

    class _EmptyAdapter:
        def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
            return []

    planner = QueryPlanner(
        MockLLMClient(
            response=json.dumps(
                {
                    "direction_en": "test query",
                    "english_query": "test query",
                    "core_terms": ["test"],
                    "search_intents": ["GENERAL"],
                }
            )
        )
    )

    runner = DirectionRunner(
        workspace=workspace,
        query_planner=planner,
        arxiv_adapter=_FailingAdapter(),
        openalex_adapter=_EmptyAdapter(),
        sources=["arxiv", "openalex"],
    )

    bundle = await runner.run("test query", direction_id="fail-test")

    # Must have acquisition failure warning in bundle
    has_failure_warning = any("ACQUISITION_FAILED" in w for w in bundle.warnings)
    assert has_failure_warning, (
        f"Expected ACQUISITION_FAILED warning, got: {bundle.warnings}"
    )

    # Warning must also be in candidate_pool.json artifact
    assert any("ACQUISITION_FAILED" in w for w in bundle.candidate_pool.warnings), (
        f"candidate_pool.warnings missing failure: {bundle.candidate_pool.warnings}"
    )

    # search_log must record the failure
    assert any("failed" in entry for entry in bundle.candidate_pool.search_log), (
        f"search_log missing failure entry: {bundle.candidate_pool.search_log}"
    )


# ---------------------------------------------------------------------------
# Test 6: M1 query planning requires LLM
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_planner_without_llm_blocks_m1() -> None:
    """Chinese query without LLM must not silently use a heuristic fallback."""
    planner = QueryPlanner()

    with pytest.raises(QueryPlanningError, match="REQUIRES_REAL_LLM"):
        await planner.plan("时间序列异常检测")


@pytest.mark.asyncio
async def test_direction_runner_without_llm_blocks_before_search(tmp_path: Path) -> None:
    """DirectionRunner should fail at query planning instead of searching with a bad query."""
    workspace = WorkspaceStore(tmp_path / "workspace")
    runner = DirectionRunner(
        workspace=workspace,
        query_planner=QueryPlanner(),
        sources=[],
    )

    with pytest.raises(QueryPlanningError, match="REQUIRES_REAL_LLM"):
        await runner.run("时间序列异常检测", direction_id="zh-test")


# ---------------------------------------------------------------------------
# Test 7: Dedup normalizes DOI prefix and arXiv version
# ---------------------------------------------------------------------------

def test_dedup_normalizes_doi_prefix() -> None:
    """Dedup must match DOIs regardless of https://doi.org/ prefix."""
    service = SelectionService()

    candidates = [
        CandidatePaper(
            paper_id="p1", title="Paper A",
            doi="https://doi.org/10.1234/abc", source="openalex",
        ),
        CandidatePaper(
            paper_id="p2", title="Paper A duplicate",
            doi="10.1234/abc", source="arxiv",
        ),
    ]

    result = service.deduplicate(candidates)
    assert len(result) == 1, f"DOI prefix normalization failed: {len(result)} papers"


def test_dedup_normalizes_doi_case() -> None:
    """Dedup must match DOIs case-insensitively."""
    service = SelectionService()

    candidates = [
        CandidatePaper(paper_id="p1", title="Paper A", doi="10.1234/ABC"),
        CandidatePaper(paper_id="p2", title="Paper A dup", doi="10.1234/abc"),
    ]

    result = service.deduplicate(candidates)
    assert len(result) == 1, f"DOI case normalization failed: {len(result)} papers"


def test_dedup_merges_different_arxiv_versions() -> None:
    """Different arXiv versions of the same paper should be merged for reading plan."""
    service = SelectionService()

    candidates = [
        CandidatePaper(paper_id="p1", title="Paper A", arxiv_id="2301.12345v1"),
        CandidatePaper(paper_id="p2", title="Paper A v2", arxiv_id="2301.12345v2"),
    ]

    result = service.deduplicate(candidates)
    # After normalization (strip vN), both have arxiv_id="2301.12345" → merged
    assert len(result) == 1, f"ArXiv versions should be merged: {len(result)} papers"


def test_dedup_merges_arxiv_prefix_variants() -> None:
    """'arXiv:2301.12345' and '2301.12345v1' should be merged."""
    service = SelectionService()

    candidates = [
        CandidatePaper(paper_id="p1", title="Paper A", arxiv_id="arXiv:2301.12345"),
        CandidatePaper(paper_id="p2", title="Paper A v1", arxiv_id="2301.12345v1"),
    ]

    result = service.deduplicate(candidates)
    assert len(result) == 1, f"arXiv prefix variants should be merged: {len(result)} papers"
