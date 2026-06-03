import asyncio

from backend.query import QueryService
from backend.schemas import CandidatePaper, PaperRole, ReadingPriority, SearchIntent
from backend.selection import SelectionService


def test_query_service_builds_enumerated_query_plan_for_tsad():
    plan = asyncio.run(QueryService().understand("时间序列异常检测"))

    assert plan.direction_zh == "时间序列异常检测"
    assert plan.language == "zh"
    assert SearchIntent.SURVEY_PAPER in plan.search_intents
    assert not plan.is_cross_domain


def test_selection_outputs_explainable_reading_plan_and_does_not_deep_read_noise():
    candidates = [
        CandidatePaper(
            paper_id="tranad",
            title="TranAD",
            year=2022,
            venue="Proceedings of the VLDB Endowment",
            doi="10.14778/3514061.3514067",
            citation_count=800,
            abstract="Transformer anomaly detection for multivariate time series.",
        ),
        CandidatePaper(
            paper_id="forecast",
            title="Forecasting at Scale",
            year=2017,
            venue="The American Statistician",
            citation_count=2200,
            abstract="Time series forecasting for business metrics.",
        ),
        CandidatePaper(
            paper_id="survey",
            title="A survey of intrusion detection systems",
            year=2019,
            venue="Cybersecurity",
            citation_count=1800,
            abstract="Network intrusion detection survey.",
        ),
    ]

    plan = SelectionService().build_reading_plan("时间序列异常检测", candidates)
    by_id = {item.paper.paper_id: item for item in plan.items}

    assert by_id["tranad"].priority == ReadingPriority.A_READ
    assert by_id["tranad"].role == PaperRole.TRANSFORMER_METHOD
    assert by_id["tranad"].scoring_breakdown.weighted_total > 0.7
    assert by_id["forecast"].priority == ReadingPriority.D_IGNORE
    assert by_id["survey"].priority == ReadingPriority.D_IGNORE
    assert len(plan.a_read) <= 12
