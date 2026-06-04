from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchsensei.live_eval import LiveEvalConfig, run_full_live_eval


def test_live_eval_script_exists() -> None:
    assert Path("scripts/run_live_eval.py").exists()


def test_full_live_eval_writes_report(tmp_path) -> None:
    config = LiveEvalConfig.from_env(report_dir=tmp_path)
    if not config.live_eval_enabled:
        pytest.skip("RESEARCHSENSEI_LIVE_EVAL=1 is required")

    report = run_full_live_eval(config=config, work_dir=tmp_path)
    report_path = Path(report["report_path"])

    assert report_path.exists()
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["live_eval"]["enabled"] is True
    serialized = json.dumps(loaded)
    assert "sk-" not in serialized
    assert "Bearer " not in serialized
    assert loaded["limits"]["max_live_cases"] == config.max_live_cases
    assert loaded["limits"]["max_llm_tokens"] == config.max_llm_tokens
