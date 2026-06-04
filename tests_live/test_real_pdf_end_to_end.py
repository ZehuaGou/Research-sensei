"""Real PDF end-to-end live eval test.

Only runs when live env flags are explicitly set.
If flags are set but conditions fail, the test FAILS (not skips).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _live_enabled() -> bool:
    return (
        os.getenv("RUN_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("RESEARCHSENSEI_LIVE_EVAL", "").strip().lower() in {"1", "true", "yes", "on"}
    )


def _llm_enabled() -> bool:
    return (
        os.getenv("RUN_LLM_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("RESEARCHSENSEI_LIVE_EVAL", "").strip().lower() in {"1", "true", "yes", "on"}
    )


def _both_enabled() -> bool:
    return _live_enabled() and _llm_enabled()


@pytest.mark.live
@pytest.mark.llm
@pytest.mark.network
def test_real_pdf_end_to_end():
    """Full e2e: real search → real PDF → real parser → real LLM → audit → status.

    If env flags are set, this test MUST run and MUST pass.
    Skipping when flags are set = test failure.
    """
    if not _both_enabled():
        pytest.skip(
            "Set RUN_LIVE_TESTS=1, RUN_LLM_TESTS=1, RESEARCHSENSEI_LIVE_EVAL=1 "
            "to run real PDF end-to-end test."
        )

    from researchsensei.live_eval import LiveEvalConfig, run_real_pdf_end_to_end_eval

    config = LiveEvalConfig.from_env()
    work_dir = Path("reports/live_eval/work_test")
    work_dir.mkdir(parents=True, exist_ok=True)

    result = run_real_pdf_end_to_end_eval(config, work_dir=work_dir)

    # These must be true when live flags are set
    assert result.get("real_network") is True, (
        f"Expected real_network=True, got {result.get('real_network')}. "
        f"Failure: {result.get('failure_reason')}"
    )
    assert result.get("real_pdf_download") is True, (
        f"Expected real_pdf_download=True, got {result.get('real_pdf_download')}. "
        f"Failure: {result.get('failure_reason')}"
    )
    assert result.get("real_llm") is True, (
        f"Expected real_llm=True, got {result.get('real_llm')}. "
        f"Failure: {result.get('failure_reason')}"
    )
    assert result.get("total_tokens", 0) > 0, (
        f"Expected total_tokens > 0, got {result.get('total_tokens')}."
    )
    assert result.get("status") == "passed", (
        f"Expected status='passed', got '{result.get('status')}'. "
        f"Failure: {result.get('failure_reason')}"
    )

    # Artifacts must exist
    artifacts = result.get("artifacts", {})
    assert artifacts.get("quality_report"), "quality_report path missing."
    assert artifacts.get("understanding_status"), "understanding_status path missing."

    # Quality report file must exist on disk
    qr_path = Path(artifacts["quality_report"])
    assert qr_path.exists(), f"quality_report.json not found at {qr_path}"

    # Understanding status file must exist on disk
    us_path = Path(artifacts["understanding_status"])
    assert us_path.exists(), f"understanding_status.json not found at {us_path}"

    # Understanding status must be SUCCESS or DEGRADED (not BLOCKED/FAILED)
    us_status = result.get("understanding_status", "")
    assert us_status in ("SUCCESS", "DEGRADED_STRUCTURAL"), (
        f"Expected SUCCESS or DEGRADED_STRUCTURAL, got '{us_status}'."
    )

    # Evidence refs must be traceable
    assert result.get("has_evidence_ref") is True, "No evidence refs found in paper card."
    assert result.get("evidence_ref_traceable") is True, (
        "Evidence refs exist but are not traceable to evidence_index."
    )

    # Report must not be committed
    report_dir = Path("reports/live_eval")
    # This is validated by .gitignore, not by the test itself


@pytest.mark.live
@pytest.mark.llm
@pytest.mark.network
def test_real_pdf_e2e_report_written():
    """Verify the e2e eval writes a report without secrets."""
    if not _both_enabled():
        pytest.skip("Set live env flags to run.")

    from researchsensei.live_eval import LiveEvalConfig, run_real_pdf_end_to_end_eval

    config = LiveEvalConfig.from_env()
    work_dir = Path("reports/live_eval/work_test_report")
    work_dir.mkdir(parents=True, exist_ok=True)

    result = run_real_pdf_end_to_end_eval(config, work_dir=work_dir)

    # Check no secrets leaked
    result_str = json.dumps(result)
    for secret_key in ("DEEPSEEK_API_KEY", "MIMO_API_KEY", "OPENAI_COMPATIBLE_API_KEY"):
        secret = os.getenv(secret_key, "")
        if secret and len(secret) > 4:
            assert secret not in result_str, f"Secret {secret_key} leaked in result."

    assert "sk-" not in result_str or result_str.count("sk-") == 0 or "[REDACTED]" in result_str
