from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchsensei.direction.exploration import (
    DirectionExplorationService,
    build_heuristic_query_plan,
)
from researchsensei.ranking import PaperRanker, select_downloads
from researchsensei.relevance import (
    MIN_DEEP_READ_RELEVANCE_SCORE,
    DeterministicRelevanceEvaluator,
)
from researchsensei.schemas import (
    CandidatePaper,
    SourceResolutionResult,
    VerificationStatus,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "m1_relevance_benchmark.json"


def _benchmark() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _cases() -> list[dict[str, object]]:
    raw = _benchmark()["cases"]
    assert isinstance(raw, list)
    return raw


def _paper(case_id: str, index: int, raw: dict[str, object]) -> CandidatePaper:
    return CandidatePaper(
        paper_id=f"{case_id}-{index}",
        title=str(raw["title"]),
        abstract=str(raw.get("abstract", "")),
        source="offline_fixture",
        sources=["offline_fixture"],
        source_confidence="high",
        metadata_confidence="high",
    )


def test_relevance_benchmark_has_required_fixed_offline_coverage() -> None:
    benchmark = _benchmark()
    cases = _cases()

    assert benchmark["schema_version"] == "m1_relevance_benchmark.v1"
    assert benchmark["minimum_case_pass_rate"] == 1.0
    assert len(cases) >= 20
    assert any(any("\u4e00" <= char <= "\u9fff" for char in str(case["query"])) for case in cases)
    assert any(
        any("\u4e00" <= char <= "\u9fff" for char in str(case["query"]))
        and any(char.isascii() and char.isalpha() for char in str(case["query"]))
        for case in cases
    )
    required_union = {
        concept
        for case in cases
        for concept in case["required_concepts"]  # type: ignore[union-attr]
    }
    assert {
        "time_series",
        "multivariate",
        "anomaly_detection",
        "forecasting",
        "imputation",
        "graph",
        "gnn",
        "diffusion",
        "survey",
        "root_cause_analysis",
        "llm",
        "aiops",
    } <= required_union


@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["id"]))
def test_offline_relevance_benchmark_case(case: dict[str, object]) -> None:
    evaluator = DeterministicRelevanceEvaluator()
    plan = build_heuristic_query_plan(str(case["query"]))
    requirements = evaluator.requirements(plan)

    assert set(requirements.required_concepts) == set(case["required_concepts"])
    assert set(requirements.optional_concepts) == set(case["optional_concepts"])
    assert set(case["forbidden_intent_mismatches"]) <= set(requirements.forbidden_intent_mismatches)
    assert requirements.allow_survey is case["allow_survey"]

    for index, raw in enumerate(case["acceptable_candidates"]):  # type: ignore[union-attr]
        candidate = _paper(str(case["id"]), index, raw)
        result = evaluator.evaluate_candidate(plan, candidate)
        assert result.relevance_gate_passed, result.relevance_reason
        assert result.rule_relevance_score >= MIN_DEEP_READ_RELEVANCE_SCORE
        assert result.missing_concepts == []

    for index, raw in enumerate(case["unacceptable_candidates"]):  # type: ignore[union-attr]
        candidate = _paper(str(case["id"]), index + 100, raw)
        result = evaluator.evaluate_candidate(plan, candidate)
        assert not result.relevance_gate_passed, (
            f"{case['id']}:{raw.get('failure')}: {result.relevance_reason}"
        )
        assert result.missing_concepts or result.forbidden_intent_matches


def test_llm_high_score_cannot_rescue_deterministic_task_mismatch() -> None:
    evaluator = DeterministicRelevanceEvaluator()
    plan = build_heuristic_query_plan("diffusion models for forecasting")
    wrong_task = CandidatePaper(
        paper_id="wrong-task",
        title="Diffusion Models for Time Series Imputation",
        abstract="A diffusion model imputes missing values.",
        llm_relevance_score=0.99,
        llm_relevance_label="HIGH",
    )

    result = evaluator.evaluate_candidate(plan, wrong_task)

    assert result.relevance_gate_evaluated is True
    assert result.relevance_gate_passed is False
    assert "forecasting" in result.missing_concepts
    assert "task_mismatch:imputation" in result.forbidden_intent_matches


def test_relevance_cleared_candidate_becomes_top1_and_only_it_is_downloaded() -> None:
    evaluator = DeterministicRelevanceEvaluator()
    plan = build_heuristic_query_plan("multivariate time series forecasting")
    wrong_top_search_result = CandidatePaper(
        paper_id="historical-wrong-top1",
        title="Multivariate Time Series Anomaly Detection",
        abstract="We detect anomalies across multiple sensor variables.",
        search_rank=1,
        rerank_rank=1,
    )
    correct = CandidatePaper(
        paper_id="correct-forecasting",
        title="Multivariate Time Series Forecasting",
        abstract="We forecast future values for multiple temporal variables.",
        search_rank=2,
        rerank_rank=2,
    )

    ranked = evaluator.evaluate_and_rank(plan, [wrong_top_search_result, correct])
    selected = select_downloads(
        ranked,
        max_download_candidates=5,
        require_relevance_gate=True,
    )

    assert [paper.paper_id for paper in ranked] == ["correct-forecasting", "historical-wrong-top1"]
    assert selected[0].download_selected is True
    assert selected[1].download_selected is False
    assert selected[1].download_decision == "SKIPPED_RELEVANCE_GATE"


class _StaticAdapter:
    def __init__(self, papers: list[CandidatePaper]) -> None:
        self.papers = papers

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return self.papers[:max_results]


class _StaticVerifier:
    def verify_batch(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        return [
            candidate.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFIED,
                    "verification_method": "offline_fixture",
                    "verification_confidence": "high",
                }
            )
            for candidate in candidates
        ]


class _NoNetworkFulltextResolver:
    def resolve_many(
        self,
        candidates: list[CandidatePaper],
        *,
        download_top_n: int = 0,
    ) -> tuple[list[CandidatePaper], list[dict[str, object]]]:
        return candidates, []


class _RecordingSourceResolver:
    def __init__(self) -> None:
        self.received: list[str] = []

    def resolve_many(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        download_dir: str | Path | None = None,
    ) -> SourceResolutionResult:
        self.received = [candidate.paper_id for candidate in candidates]
        return SourceResolutionResult(query=query)


def test_pipeline_success_and_relevance_failure_are_independent_bundle_states() -> None:
    resolver = _RecordingSourceResolver()
    service = DirectionExplorationService(
        adapters={
            "fixture": _StaticAdapter(
                [
                    CandidatePaper(
                        paper_id="off-topic",
                        title="Image Classification with Convolutional Networks",
                        abstract="We classify images.",
                    )
                ]
            )
        },
        sources=["fixture"],
        verifier=_StaticVerifier(),  # type: ignore[arg-type]
        fulltext_resolver=_NoNetworkFulltextResolver(),  # type: ignore[arg-type]
        source_resolver=resolver,  # type: ignore[arg-type]
        paper_ranker=PaperRanker(enabled=False),
    )

    bundle = service.explore("time series anomaly detection")

    assert bundle.pipeline_status.status == "SUCCESS"
    assert bundle.pipeline_status.details["m2_completed"] is False
    assert bundle.relevance_status.status == "BLOCKED"
    assert bundle.relevance_status.code == "NO_CANDIDATE_PASSED_RELEVANCE_GATE"
    assert bundle.source_status.status == "BLOCKED"
    assert bundle.understanding_status.status == "BLOCKED"
    assert bundle.status == "DEGRADED"
    assert resolver.received == []
    assert bundle.candidate_cards[0]["download_decision"] == "SKIPPED_RELEVANCE_GATE"
