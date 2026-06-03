from pathlib import Path

import pytest

from backend.pipeline import ResearchSenseiPipeline
from backend.schemas import CandidatePaper, ReadingPriority


@pytest.mark.asyncio
async def test_direction_pipeline_produces_limited_a_read_plan() -> None:
    pipeline = ResearchSenseiPipeline()
    bundle = await pipeline.plan_direction(
        "时间序列异常检测",
        [
            CandidatePaper(
                paper_id="tranad",
                title="TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data",
                year=2022,
                venue="Proceedings of the VLDB Endowment",
                citation_count=600,
                abstract="Transformer anomaly detection for multivariate time series.",
            ),
            CandidatePaper(
                paper_id="forecast",
                title="Forecasting at Scale",
                year=2017,
                venue="The American Statistician",
                abstract="A forecasting system for time series.",
            ),
        ],
        max_a_read=1,
    )

    assert bundle.query_plan.direction_zh == "时间序列异常检测"
    assert len(bundle.reading_plan.a_read) == 1
    ignored = [item for item in bundle.reading_plan.items if item.paper.paper_id == "forecast"][0]
    assert ignored.priority == ReadingPriority.D_IGNORE


@pytest.mark.asyncio
async def test_single_paper_pipeline_builds_all_learning_artifacts() -> None:
    pipeline = ResearchSenseiPipeline()
    bundle = await pipeline.build_paper_learning_bundle(
        "sample_tsad",
        """
        Abstract
        We study anomaly detection in multivariate time series.

        Method
        The model optimizes L = L_task + lambda L_reg to learn stable temporal dependencies.

        Experiments
        Experiments compare baselines and ablations on benchmark datasets.
        """,
    )

    assert bundle.document.blocks
    assert bundle.evidence.claims
    assert bundle.skeleton.objective
    assert bundle.paper_card.thirty_second
    assert bundle.formula_cards[0].numeric_example
    assert bundle.pattern_card.transfer_template
    assert bundle.drill_card.advisor_questions


def test_attention_sample_outputs_exist() -> None:
    sample_dir = Path("outputs/sample")
    required = [
        "paper_skeleton.json",
        "formula_cards/formula_01.json",
        "formula_cards/formula_02.json",
        "formula_cards/formula_03.json",
        "pattern_card.json",
        "drill_card.json",
        "paper_card.html",
    ]
    for relative_path in required:
        assert (sample_dir / relative_path).exists()
