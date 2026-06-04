from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from researchsensei.live_eval import LiveEvalConfig, run_full_live_eval


def _live_m1_enabled() -> bool:
    return (
        os.getenv("RUN_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("RUN_LLM_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("RESEARCHSENSEI_LIVE_EVAL", "").strip().lower() in {"1", "true", "yes", "on"}
    )


def test_live_config_defaults_do_not_enable_network(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("RUN_LIVE_TESTS", raising=False)
    monkeypatch.delenv("RUN_LLM_TESTS", raising=False)
    monkeypatch.delenv("RESEARCHSENSEI_LIVE_EVAL", raising=False)

    config = LiveEvalConfig.from_env(report_dir=tmp_path)

    assert config.run_live_tests is False
    assert config.run_llm_tests is False
    assert config.live_eval_enabled is False
    assert config.live_skip_reason() == "RUN_LIVE_TESTS=1 and RESEARCHSENSEI_LIVE_EVAL=1 are required"


@pytest.mark.live
@pytest.mark.llm
@pytest.mark.network
def test_m1_real_llm_multisource_pdf_acquisition_and_report(tmp_path) -> None:
    if not _live_m1_enabled():
        pytest.skip("Set RUN_LIVE_TESTS=1, RUN_LLM_TESTS=1, and RESEARCHSENSEI_LIVE_EVAL=1 to run M1 live eval.")

    config = LiveEvalConfig.from_env(report_dir=tmp_path)
    report = run_full_live_eval(config=config, work_dir=tmp_path / "work")
    result = report["m1_live"]

    assert result["status"] == "passed", result.get("failure_reason", "")
    assert result["real_network"] is True
    assert result["real_llm_query_planning"] is True
    assert result["english_query"]
    assert len(result["sources_attempted"]) >= 4
    assert len(result["sources_success"]) >= 1
    assert result["candidate_count"] >= 1
    assert result["dedup_after"] <= result["dedup_before"]
    assert result["pdf_url_count"] >= 1
    assert result["pdf_download_success_count"] >= 1
    assert result["a_read_count"] >= 1
    assert result["a_read_can_enter_m2_count"] == result["a_read_count"]
    assert result["reading_plan_status"] == "OK"
    assert result["token_usage"]["total_tokens"] > 0
    assert result["estimated_cost_usd"] <= config.max_llm_cost_usd

    for path in result["artifacts"].values():
        assert Path(path).exists(), f"Missing artifact: {path}"
    assert all(item["sha256"] and Path(item["local_path"]).exists() for item in result["downloaded_sources"])
    report_path = Path(report["report_path"])
    assert report_path.exists()
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "v2-m1-real"
    assert loaded["m1_live"]["status"] == "passed", loaded["m1_live"].get("failure_reason", "")
    assert loaded["m1_live"]["real_llm_query_planning"] is True
    assert loaded["m1_live"]["pdf_download_success_count"] >= 1
    serialized = json.dumps(loaded)
    for secret_key in ("DEEPSEEK_API_KEY", "MIMO_API_KEY", "OPENAI_COMPATIBLE_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"):
        secret = os.getenv(secret_key, "")
        if secret:
            assert secret not in serialized
    assert "Bearer " not in serialized
