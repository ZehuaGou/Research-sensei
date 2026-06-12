from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.test_m2_understanding import _write_m1_bundle


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_target_mode_eval_writes_static_contract_reports_without_full_mineru(tmp_path: Path) -> None:
    from m1_target_mode_eval import run_target_mode_eval

    artifact_dir = _write_m1_bundle(tmp_path / "m1_demo")
    output_dir = tmp_path / "target_eval"
    candidates = [
        {"arxiv_id": "2510.18998", "title": "Known tuned paper", "abstract": "old", "pdf_url": "", "published": "2025-10-21"},
        {"arxiv_id": "2601.00001", "title": "Unseen Transformer Time Series Anomaly Detection", "abstract": "deep learning time series anomaly detection", "pdf_url": "https://arxiv.org/pdf/2601.00001", "published": "2026-01-01"},
        {"arxiv_id": "2601.00002", "title": "Unseen Diffusion Model for Multivariate Time Series", "abstract": "diffusion model for deep learning time series", "pdf_url": "https://arxiv.org/pdf/2601.00002", "published": "2026-01-02"},
    ]

    result = run_target_mode_eval(
        output_dir=output_dir,
        candidates=candidates,
        artifact_dirs=[artifact_dir],
        run_live_eval=False,
    )

    assert result["summary"]["full_mineru_enabled"] is False
    assert result["summary"]["live_eval_ran"] is False
    assert result["summary"]["unseen_candidate_count"] >= 2
    assert {c["arxiv_id"] for c in result["selected_unseen_candidates"]} == {"2601.00001", "2601.00002"}
    assert result["contract_checks"][0]["status"] == "PASS"
    assert result["contract_checks"][0]["checks"]["performance_gate_not_promoted"] == "PASS"
    for name in [
        "target_eval_config.json",
        "target_candidate_papers.json",
        "target_eval_report.md",
        "target_eval_results.json",
        "overfit_risk_report.md",
        "failure_cases.md",
    ]:
        assert (output_dir / name).exists(), name

    config = json.loads((output_dir / "target_eval_config.json").read_text(encoding="utf-8"))
    assert config["full_mineru_enabled"] is False
    assert config["max_live_eval_pages"] == 3


def test_target_mode_contract_fails_when_reference_formulas_are_counted_as_core(tmp_path: Path) -> None:
    from m1_target_mode_eval import run_target_mode_eval

    artifact_dir = _write_m1_bundle(tmp_path / "m1_demo")
    slots = json.loads((artifact_dir / "formula_slots.json").read_text(encoding="utf-8"))
    for slot in slots:
        slot["section"] = "References"
    (artifact_dir / "formula_slots.json").write_text(json.dumps(slots, indent=2), encoding="utf-8")

    result = run_target_mode_eval(
        output_dir=tmp_path / "target_eval",
        candidates=[
            {"arxiv_id": "2601.00001", "title": "Unseen Transformer Time Series Anomaly Detection", "abstract": "time series anomaly", "pdf_url": "https://arxiv.org/pdf/2601.00001", "published": "2026-01-01"},
            {"arxiv_id": "2601.00002", "title": "Unseen Diffusion Time Series", "abstract": "time series anomaly", "pdf_url": "https://arxiv.org/pdf/2601.00002", "published": "2026-01-02"},
        ],
        artifact_dirs=[artifact_dir],
        run_live_eval=False,
    )

    check = result["contract_checks"][0]
    assert check["status"] == "FAIL"
    assert check["checks"]["reference_formula_exclusion"] == "FAIL"


def test_production_hardcode_detection_flags_fixture_but_not_current_source(tmp_path: Path) -> None:
    from m1_target_mode_eval import detect_production_hardcodes

    fixture_root = tmp_path / "fixture"
    (fixture_root / "src").mkdir(parents=True)
    (fixture_root / "scripts").mkdir()
    (fixture_root / "src" / "bad.py").write_text('PAPER = "2510.18998"\n', encoding="utf-8")
    violations = detect_production_hardcodes(fixture_root)
    assert violations
    assert violations[0]["pattern"] == "2510.18998"

    current = detect_production_hardcodes(ROOT)
    assert current == []
