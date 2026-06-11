"""Tests for M1 paper search defaults, device diagnosis, and acceptance runner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Search defaults ──

def test_search_default_max_pdf_downloads():
    """Default max_pdf_downloads must be 3."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import parse_args
    args = parse_args([])
    assert args.max_pdf_downloads == 3


def test_search_default_max_results_per_query():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import parse_args
    args = parse_args([])
    assert args.max_results_per_query == 10


def test_search_default_full_parse_limit():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import parse_args
    args = parse_args([])
    assert args.full_parse_limit == 1


def test_search_dry_run_no_downloads(tmp_path):
    """Dry-run should not download any PDFs."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import main as search_main

    out_dir = tmp_path / "search_out"
    # Patch sys.argv
    old_argv = sys.argv
    try:
        sys.argv = [
            "m1_unseen_paper_search.py",
            "--output-dir", str(out_dir),
            "--max-results-per-query", "2",
            "--max-pdf-downloads", "3",
            "--dry-run",
        ]
        rc = search_main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    # No _downloads directory should be created in dry-run
    assert not (out_dir / "_downloads").exists()
    # search_config.json should exist with correct values
    config = json.loads((out_dir / "search_config.json").read_text())
    assert config["cli_args"]["max_pdf_downloads"] == 3
    assert config["cli_args"]["dry_run"] is True


def test_search_config_json_has_correct_defaults(tmp_path):
    """search_config.json cli_args must match actual defaults."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import main as search_main

    out_dir = tmp_path / "search_out"
    old_argv = sys.argv
    try:
        sys.argv = [
            "m1_unseen_paper_search.py",
            "--output-dir", str(out_dir),
            "--max-results-per-query", "2",
            "--dry-run",
        ]
        search_main()
    finally:
        sys.argv = old_argv

    config = json.loads((out_dir / "search_config.json").read_text())
    # These must match argparse defaults
    assert config["cli_args"]["max_pdf_downloads"] == 3
    assert config["cli_args"]["max_results_per_query"] == 2
    assert config["cli_args"]["full_parse_limit"] == 1
    assert config["cli_args"]["dry_run"] is True


def test_search_report_contains_correct_max(tmp_path):
    """search_config.json must reflect the actual max_pdf_downloads passed."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import main as search_main

    out_dir = tmp_path / "search_out"
    old_argv = sys.argv
    try:
        sys.argv = [
            "m1_unseen_paper_search.py",
            "--output-dir", str(out_dir),
            "--max-results-per-query", "5",
            "--max-pdf-downloads", "3",
            "--dry-run",
        ]
        search_main()
    finally:
        sys.argv = old_argv

    config = json.loads((out_dir / "search_config.json").read_text())
    assert config["cli_args"]["max_pdf_downloads"] == 3
    # In dry-run, stage_b_stats is empty (Stage B never executed)
    # But cli_args must still reflect the correct max
    assert config["cli_args"]["max_pdf_downloads"] == 3


def test_docstring_default_matches_argparse():
    """Docstring declared default must match argparse default."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import parse_args

    args = parse_args([])
    # Read docstring from module
    import m1_unseen_paper_search as mod
    doc = mod.__doc__
    assert doc is not None
    assert f"--max-pdf-downloads {args.max_pdf_downloads}" in doc


def test_report_md_contains_correct_max(tmp_path):
    """paper_search_report.md must reference the correct max_pdf_downloads."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import _write_outputs, parse_args
    import datetime

    args = parse_args(["--output-dir", str(tmp_path), "--max-results-per-query", "2", "--dry-run"])
    out = tmp_path
    out.mkdir(parents=True, exist_ok=True)

    # Simulate a minimal candidate list with one selected
    candidates = [{
        "arxiv_id": "0000.00000",
        "title": "Test Paper",
        "abstract": "abstract",
        "pdf_url": "",
        "published": "2026-01-01",
        "authors": ["A"],
        "query": "q",
        "topic_score": 0.5,
        "formula_prescreen_count": 10,
        "formula_prescreen_note": "PyMuPDF text-line heuristic, NOT MinerU final count",
        "pdf_downloaded": True,
        "prescreen_elapsed_seconds": 0.1,
        "download_elapsed_seconds": 0.1,
        "exclusion_status": "candidate",
        "exclusion_reason": "",
        "selected_candidate": True,
    }]
    best = candidates[0]
    stats_a = {"raw_candidate_count": 1, "valid_candidate_count": 1, "excluded_count": 0, "elapsed_seconds": 0.1, "pdf_downloaded_count": 0}
    stats_b = {"stage": "B", "description": f"Limited PDF prescreen, max {args.max_pdf_downloads} downloads", "pdf_downloaded_count": 0, "cached_count": 0, "prescreened_count": 0, "valid_after_prescreen": 1, "elapsed_seconds": 0.1}

    _write_outputs(out, candidates, best, stats_a, stats_b, args)

    report_md = (out / "paper_search_report.md").read_text(encoding="utf-8")
    assert f"max {args.max_pdf_downloads}" in report_md


# ── Device diagnosis ──

def test_device_report_json_exists(tmp_path):
    """Device diagnosis should produce device_report.json."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_device_diagnosis import generate_report

    report = generate_report()
    assert "torch" in report
    assert "nvidia_smi" in report
    assert "summary" in report
    assert "gpu_available" in report["summary"]
    assert isinstance(report["summary"]["gpu_available"], bool)


def test_device_report_has_diagnostic_fields():
    """Device report must have all required diagnostic fields."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_device_diagnosis import generate_report

    report = generate_report()
    assert "python_version" in report
    assert "os" in report
    assert report["torch"]["installed"] is True
    assert "cuda_available" in report["torch"]
    assert "cuda_issues" in report
    assert isinstance(report["cuda_issues"], list)


def test_cuda_advice_not_hardcoded_to_cu121():
    """CUDA install advice must not hardcode a specific CUDA version like cu121."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_device_diagnosis import _recommendation

    # Simulate torch not installed
    torch_info = {"installed": False, "cuda_available": False}
    nvidia_info = {"available": False, "gpus": []}
    tf_info = {"installed": False}
    acc_info = {"installed": False}
    advice = _recommendation(torch_info, nvidia_info, tf_info, acc_info)
    assert "cu121" not in advice, "CUDA advice must not hardcode cu121"
    assert "pytorch.org" in advice.lower(), "CUDA advice should reference PyTorch official site"


# ── MinerU adapter device stats ──

def test_mineru_adapter_has_device_mode_param():
    """MinerU25ProAdapter must accept device_mode parameter."""
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter(device_mode="auto")
    assert adapter.device_mode == "auto"

    adapter_cpu = MinerU25ProAdapter(device_mode="cpu")
    assert adapter_cpu.device_mode == "cpu"


def test_mineru_adapter_probe_device_reports_stats():
    """MinerU25ProAdapter._probe_device() must return device stats."""
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter(device_mode="auto")
    stats = adapter._probe_device()

    assert "device_mode_requested" in stats
    assert "device_mode_actual" in stats
    assert "cuda_available" in stats
    assert "torch_installed" in stats
    assert stats["device_mode_requested"] == "auto"
    assert stats["device_mode_actual"] in ("cuda", "cpu")


def test_mineru_adapter_cpu_mode_reports_cpu():
    """device_mode=cpu must report device_mode_actual=cpu."""
    from researchsensei.canonical.mineru25_adapter import MinerU25ProAdapter

    adapter = MinerU25ProAdapter(device_mode="cpu")
    stats = adapter._probe_device()
    assert stats["device_mode_actual"] == "cpu"


# ── formula_prescreen_count labeling ──

def test_selected_metadata_has_prescreen_note(tmp_path):
    """selected_paper_metadata.json must label formula_prescreen_count as heuristic."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from m1_unseen_paper_search import main as search_main

    out_dir = tmp_path / "search_out"
    old_argv = sys.argv
    try:
        sys.argv = [
            "m1_unseen_paper_search.py",
            "--output-dir", str(out_dir),
            "--max-results-per-query", "2",
            "--max-pdf-downloads", "3",
            "--dry-run",
        ]
        search_main()
    finally:
        sys.argv = old_argv

    config = json.loads((out_dir / "search_config.json").read_text())
    assert "PyMuPDF" in config["search_cost_summary"]["note"]
    assert "NOT MinerU" in config["search_cost_summary"]["note"]
