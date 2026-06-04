from __future__ import annotations

import pytest

from researchsensei.live_eval import LiveEvalConfig, run_m2_real_llm_smoke


def test_llm_config_reports_missing_key_without_leaking_secret(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("RUN_LLM_TESTS", "1")
    monkeypatch.setenv("RESEARCHSENSEI_LIVE_EVAL", "1")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)

    config = LiveEvalConfig.from_env(report_dir=tmp_path, load_dotenv=False)
    reason = config.llm_skip_reason()

    assert "_API_KEY" in reason
    assert "sk-" not in reason


def test_m2_real_llm_smoke(tmp_path) -> None:
    config = LiveEvalConfig.from_env(report_dir=tmp_path)
    if not config.run_llm_tests or not config.live_eval_enabled:
        pytest.skip(config.llm_skip_reason())
    if config.llm_skip_reason():
        pytest.skip(config.llm_skip_reason())

    result = run_m2_real_llm_smoke(config, work_dir=tmp_path)

    assert result["status"] == "passed"
    assert result["real_llm"] is True
    assert result["model"]
    assert result["token_usage"]["total_tokens"] > 0
    assert result["estimated_cost_usd"] <= config.max_llm_cost_usd
    assert result["artifacts"]["quality_report"]
    assert result["artifacts"]["understanding_status"]
    assert result["has_evidence_ref"] is True
    assert result["evidence_ref_traceable"] is True
    assert isinstance(result["allowed_for_user_display"], bool)
