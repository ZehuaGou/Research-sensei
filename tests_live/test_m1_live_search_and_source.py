from __future__ import annotations

import pytest

from researchsensei.live_eval import LiveEvalConfig, run_m1_live_search


def test_live_config_defaults_do_not_enable_network(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("RUN_LIVE_TESTS", raising=False)
    monkeypatch.delenv("RESEARCHSENSEI_LIVE_EVAL", raising=False)

    config = LiveEvalConfig.from_env(report_dir=tmp_path)

    assert config.run_live_tests is False
    assert config.live_eval_enabled is False
    assert config.live_skip_reason() == "RUN_LIVE_TESTS=1 and RESEARCHSENSEI_LIVE_EVAL=1 are required"


def test_m1_live_search_and_source_resolution(tmp_path) -> None:
    config = LiveEvalConfig.from_env(report_dir=tmp_path)
    if not config.run_live_tests or not config.live_eval_enabled:
        pytest.skip(config.live_skip_reason())

    result = run_m1_live_search(
        config,
        query="time series anomaly detection transformer",
    )

    assert result["status"] == "passed"
    assert result["real_network"] is True
    assert result["query"] == "time series anomaly detection transformer"
    assert result["candidate_count"] >= 1
    assert result["source_resolution"]["total"] == result["candidate_count"]
    assert (
        result["source_resolution"]["resolved"]
        + result["source_resolution"]["partial"]
        + result["source_resolution"]["not_found"]
    ) == result["candidate_count"]
    arxiv_candidates = [item for item in result["sample_candidates"] if item["arxiv_id"]]
    if arxiv_candidates:
        assert result["source_resolution"]["resolved"] >= 1
    assert result["semantic_scholar_status"] == "not_implemented"
    assert result["crossref_status"] == "not_implemented"
