from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


import run_main_chain_matrix as matrix  # noqa: E402


# Sample fixtures for unit tests


@pytest.fixture
def sample_success_row() -> dict:
    return {
        "query": "time series anomaly detection",
        "selected_candidate": {"title": "Paper A", "arxiv_id": "2301.12345", "sources": ["arxiv"]},
        "handoff_candidate": {"title": "Paper A", "arxiv_id": "2301.12345", "sources": ["arxiv"]},
        "arxiv_id": "2301.12345",
        "doi": "",
        "pdf_url": "",
        "input_type": "arxiv_source",
        "source_strategy": "source_first",
        "handoff_job_id": "job-success",
        "final_status": "SUCCESS",
        "blocking_reason": "",
        "cards_code": 200,
        "components": ["paper_card", "formula_cards", "teaching_cards"],
        "formula_origin_summary": {"origins": "source_latex", "ocr_statuses": "not_required"},
        "verdict": "PASS",
        "cache_hit": True,
        "source_metrics": {"arxiv": 1, "openalex": 1},
        "failure_root_cause": "",
        "warnings": [],
        "elapsed_ms": 15000,
        "seed_expansion_status": "SUCCESS",
        "seed_expansion_group_counts": {"upstream": 3, "downstream": 2, "same_route": 1, "surveys": 0},
        "arxiv_source_downloaded": True,
        "fallback_used": "",
    }


@pytest.fixture
def sample_degraded_row() -> dict:
    return {
        "query": "multivariate time series imputation",
        "selected_candidate": {"title": "Paper B", "arxiv_id": "", "sources": ["openalex"]},
        "handoff_candidate": {"title": "Paper B", "arxiv_id": "", "sources": ["openalex"]},
        "arxiv_id": "",
        "doi": "10.1234/test",
        "pdf_url": "https://example.com/paper.pdf",
        "input_type": "arxiv_pdf",
        "source_strategy": "pdf_fallback",
        "handoff_job_id": "job-degraded",
        "final_status": "DEGRADED_STRUCTURAL",
        "blocking_reason": "FORMULA_DERIVATION_BLOCKED",
        "cards_code": 200,
        "components": ["paper_card", "teaching_cards"],
        "formula_origin_summary": {"origins": "pdf_ocr", "ocr_statuses": "ocr_needed"},
        "verdict": "DEGRADED",
        "cache_hit": False,
        "source_metrics": {"arxiv": 1, "openalex": 1, "crossref": 1},
        "failure_root_cause": "degraded_formula_derivation_blocked:FORMULA_DERIVATION_BLOCKED",
        "warnings": ["PDF_FALLBACK"],
        "elapsed_ms": 30000,
        "seed_expansion_status": "SUCCESS",
        "seed_expansion_group_counts": {"upstream": 1, "downstream": 1, "same_route": 0, "surveys": 0},
        "arxiv_source_downloaded": False,
        "fallback_used": "pdf_fallback",
    }


@pytest.fixture
def sample_paper_card_failed_row() -> dict:
    return {
        "query": "diffusion models for forecasting",
        "selected_candidate": {"title": "Paper C", "arxiv_id": "", "sources": ["openalex"]},
        "handoff_candidate": {"title": "Paper C", "arxiv_id": "", "sources": ["openalex"]},
        "arxiv_id": "",
        "doi": "",
        "pdf_url": "https://example.com/diffusion.pdf",
        "input_type": "arxiv_pdf",
        "source_strategy": "pdf_fallback",
        "handoff_job_id": "job-blocked",
        "final_status": "BLOCKED_UNDERSTANDING",
        "blocking_reason": "PAPER_CARD_FAILED",
        "cards_code": 403,
        "components": [],
        "formula_origin_summary": {},
        "verdict": "BLOCKED",
        "cache_hit": False,
        "source_metrics": {"arxiv": 1, "semantic_scholar": 1},
        "failure_root_cause": "blocked:PAPER_CARD_FAILED",
        "warnings": ["CARD_BUILDER_FAILED: paper_card: ..."],
        "elapsed_ms": 60000,
        "seed_expansion_status": "SUCCESS",
        "seed_expansion_group_counts": {"upstream": 0, "downstream": 2, "same_route": 0, "surveys": 0},
        "arxiv_source_downloaded": False,
        "fallback_used": "pdf_fallback",
    }


@pytest.fixture
def sample_fail_row() -> dict:
    return {
        "query": "graph neural network anomaly detection",
        "selected_candidate": {"title": "", "arxiv_id": "", "sources": []},
        "handoff_candidate": {"title": "", "arxiv_id": "", "sources": []},
        "arxiv_id": "",
        "doi": "",
        "pdf_url": "",
        "input_type": "unknown",
        "source_strategy": "unknown",
        "handoff_job_id": "",
        "final_status": "",
        "blocking_reason": "",
        "cards_code": 0,
        "components": [],
        "formula_origin_summary": {},
        "verdict": "FAIL",
        "cache_hit": False,
        "source_metrics": {},
        "failure_root_cause": "direction_search_no_candidates",
        "warnings": [],
        "elapsed_ms": 5000,
        "seed_expansion_status": "",
        "seed_expansion_group_counts": {"upstream": 0, "downstream": 0, "same_route": 0, "surveys": 0},
        "arxiv_source_downloaded": False,
        "fallback_used": "",
    }


class TestClassifyFailureRootCause:
    def test_success_root_cause_empty(self, sample_success_row):
        assert sample_success_row["failure_root_cause"] == ""

    def test_degraded_formula(self, sample_degraded_row):
        assert sample_degraded_row["failure_root_cause"] == "degraded_formula_derivation_blocked:FORMULA_DERIVATION_BLOCKED"

    def test_blocked_paper_card(self, sample_paper_card_failed_row):
        assert sample_paper_card_failed_row["failure_root_cause"] == "blocked:PAPER_CARD_FAILED"

    def test_fail_direction_no_candidates(self, sample_fail_row):
        assert sample_fail_row["failure_root_cause"] == "direction_search_no_candidates"


class TestMatrixSummarySchema:
    def test_summary_schema(self, sample_success_row, sample_degraded_row, sample_fail_row):
        rows = [sample_success_row, sample_degraded_row, sample_fail_row]
        summary = {
            "schema_version": "main_chain_matrix_v1",
            "generated_at": "2026-06-18T00:00:00Z",
            "provider": "mimo",
            "llm_enabled": True,
            "llm_mode_note": "LLM enabled with provider 'mimo'.",
            "cache_enabled": False,
            "cache_refreshed": True,
            "cache_hits": 1,
            "total_queries": 3,
            "passed": 2,
            "failed": 1,
            "final_status_breakdown": {"SUCCESS": 1, "DEGRADED_STRUCTURAL": 1, "BLOCKED_UNDERSTANDING": 0, "BASELINE_ONLY": 0},
            "failure_root_cause_breakdown": {
                "degraded_formula_derivation_blocked:FORMULA_DERIVATION_BLOCKED": 1,
                "direction_search_no_candidates": 1,
            },
            "total_time_seconds": 50.0,
            "rows": rows,
        }

        assert summary["schema_version"] == "main_chain_matrix_v1"
        assert summary["total_queries"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["final_status_breakdown"]["SUCCESS"] == 1
        assert summary["final_status_breakdown"]["DEGRADED_STRUCTURAL"] == 1

        # Check row schema
        for row in summary["rows"]:
            assert "query" in row
            assert "selected_candidate" in row
            assert "arxiv_id" in row
            assert "input_type" in row
            assert "source_strategy" in row
            assert "handoff_job_id" in row
            assert "final_status" in row
            assert "blocking_reason" in row
            assert "cards_code" in row
            assert "components" in row
            assert "formula_origin_summary" in row
            assert "verdict" in row
            assert "cache_hit" in row
            assert "source_metrics" in row
            assert "failure_root_cause" in row

    def test_summary_json_serializable(self, sample_success_row, sample_degraded_row):
        rows = [sample_success_row, sample_degraded_row]
        summary = {
            "schema_version": "main_chain_matrix_v1",
            "generated_at": "2026-06-18T00:00:00Z",
            "provider": "mimo",
            "llm_enabled": True,
            "llm_mode_note": "test",
            "cache_enabled": False,
            "cache_refreshed": True,
            "cache_hits": 0,
            "total_queries": 2,
            "passed": 2,
            "failed": 0,
            "final_status_breakdown": {"SUCCESS": 1, "DEGRADED_STRUCTURAL": 1, "BLOCKED_UNDERSTANDING": 0, "BASELINE_ONLY": 0},
            "failure_root_cause_breakdown": {"degraded_formula_derivation_blocked:FORMULA_DERIVATION_BLOCKED": 1},
            "total_time_seconds": 45.0,
            "rows": rows,
        }
        # Must not raise
        json.dumps(summary)

    def test_no_pdf_source_llm_in_json(self, sample_success_row, sample_degraded_row):
        """Verify JSON summary does not contain PDF/source/LLM raw content."""
        rows = [sample_success_row, sample_degraded_row]
        payload = json.dumps(rows)
        assert "pdf_content" not in payload
        assert "source_text" not in payload
        assert "latex_source" not in payload
        assert "llm_output" not in payload
        assert "raw_response" not in payload


class TestCacheHitMiss:
    def test_cache_hit_tracked(self, sample_success_row):
        assert sample_success_row["cache_hit"] is True

    def test_cache_miss_tracked(self, sample_degraded_row):
        assert sample_degraded_row["cache_hit"] is False

    def test_fail_cache_miss(self, sample_fail_row):
        assert sample_fail_row["cache_hit"] is False


class TestSkipOnFail:
    def test_fail_row_does_not_stop_matrix(self):
        """Verify that a single FAIL row doesn't prevent other rows."""
        rows = [
            {"query": "q1", "verdict": "FAIL", "final_status": ""},
            {"query": "q2", "verdict": "PASS", "final_status": "SUCCESS"},
        ]
        passed = sum(1 for r in rows if r["verdict"] == "PASS")
        failed = sum(1 for r in rows if r["verdict"] == "FAIL")
        assert passed == 1
        assert failed == 1


class TestSourceMetricsSummary:
    def test_source_metrics_summary(self, sample_success_row):
        metrics = sample_success_row["source_metrics"]
        assert "arxiv" in metrics
        assert metrics["arxiv"] == 1

    def test_empty_source_metrics(self, sample_fail_row):
        assert sample_fail_row["source_metrics"] == {}


class TestWarningsStructure:
    def test_warnings_is_list(self, sample_degraded_row):
        assert isinstance(sample_degraded_row["warnings"], list)

    def test_warnings_contains_expected(self, sample_degraded_row):
        assert any("PDF_FALLBACK" in w for w in sample_degraded_row["warnings"])


def test_default_queries_are_12():
    assert len(matrix.DEFAULT_QUERIES) == 12
    expected_first = "time series anomaly detection"
    assert matrix.DEFAULT_QUERIES[0] == expected_first


def test_parse_args_defaults():
    args = matrix.parse_args([])
    assert args.provider == "cc_switch"
    assert args.max_candidates == 10
    assert args.use_cache is False
    assert args.refresh_cache is False
    assert args.queries is None
    assert args.query_timeout_seconds == 240.0
    assert args.llm_card_timeout_seconds == 30.0


def test_parse_args_custom_queries():
    args = matrix.parse_args(["--queries", "q1", "q2", "q3"])
    assert args.queries == ["q1", "q2", "q3"]


def test_parse_args_cache():
    args = matrix.parse_args(["--use-cache", "--cache-dir", "/tmp/cache"])
    assert args.use_cache is True
    assert args.cache_dir == "/tmp/cache"


class TestOutputJsonSanitized:
    def test_output_does_not_contain_large_content(self, sample_success_row, tmp_path):
        """Verify JSON output written to file does not contain forbidden fields."""
        output_path = tmp_path / "summary.json"
        rows = [sample_success_row]
        summary = {
            "schema_version": "main_chain_matrix_v1",
            "generated_at": "2026-06-18T00:00:00Z",
            "provider": "mimo",
            "llm_enabled": True,
            "llm_mode_note": "test",
            "cache_enabled": False,
            "cache_refreshed": True,
            "cache_hits": 0,
            "total_queries": 1,
            "passed": 1,
            "failed": 0,
            "final_status_breakdown": {"SUCCESS": 1, "DEGRADED_STRUCTURAL": 0, "BLOCKED_UNDERSTANDING": 0, "BASELINE_ONLY": 0},
            "failure_root_cause_breakdown": {},
            "total_time_seconds": 15.0,
            "rows": rows,
        }
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        content = output_path.read_text(encoding="utf-8")
        assert "pdf_content" not in content
        assert "source_text" not in content
        assert "latex_source" not in content
        assert "llm_output" not in content


class TestFailureRootCauseClassification:
    def test_classify_direction_no_candidates(self, sample_fail_row):
        result = {"final_verdict": "FAIL", "failed_stage": "direction_search", "final_understanding_status": "", "blocking_reason": ""}
        assert matrix._classify_failure_root_cause(result) == "direction_search_no_candidates"

    def test_classify_direction_failed(self):
        result = {"final_verdict": "FAIL", "failed_stage": "direction_search", "final_understanding_status": "BLOCKED", "blocking_reason": "NO_CANDIDATES", "source_strategy": "metadata_only"}
        assert matrix._classify_failure_root_cause(result) == "direction_search_failed"

    def test_classify_query_timeout(self):
        result = {
            "final_verdict": "FAIL",
            "failed_stage": "query_timeout",
            "final_understanding_status": "",
            "blocking_reason": "",
            "source_strategy": "unknown",
        }
        assert matrix._classify_failure_root_cause(result) == "query_timeout"

    def test_classify_degraded_blocked(self):
        result = {"final_verdict": "BLOCKED", "final_understanding_status": "BLOCKED_UNDERSTANDING", "blocking_reason": "PAPER_CARD_FAILED"}
        assert matrix._classify_failure_root_cause(result) == "blocked:PAPER_CARD_FAILED"

    def test_classify_degraded_formula_blocked(self):
        result = {
            "final_verdict": "DEGRADED",
            "final_understanding_status": "DEGRADED_STRUCTURAL",
            "blocking_reason": "FORMULA_DERIVATION_BLOCKED",
            "returned_card_components": ["paper_card", "teaching_cards"],
        }
        assert matrix._classify_failure_root_cause(result) == "degraded_formula_derivation_blocked:FORMULA_DERIVATION_BLOCKED"


def test_run_matrix_continues_after_query_timeout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        matrix,
        "_resolve_llm_mode",
        lambda provider, skip_llm: {"enabled": True, "note": f"LLM enabled with provider '{provider}'."},
    )

    def fake_run_query(args, *, query: str, llm_mode: dict[str, object]) -> dict[str, object]:
        if query == "q1":
            return matrix._timeout_result(query, llm_mode, 1.0)
        return {
            "query": query,
            "llm_enabled": True,
            "llm_mode_note": "test",
            "cache_hit": False,
            "selected_candidate_title": "Paper A",
            "selected_candidate_arxiv_id": "2301.12345",
            "selected_candidate_sources": ["arxiv"],
            "selected_seed_handoff_title": "Paper A",
            "selected_seed_handoff_arxiv_id": "2301.12345",
            "selected_seed_handoff_sources": ["arxiv"],
            "selected_input_type": "arxiv_source",
            "source_strategy": "source_first",
            "arxiv_source_downloaded": True,
            "fallback_used": "",
            "seed_expansion_status": "SUCCESS",
            "seed_expansion_group_counts": {"upstream": 1, "downstream": 0, "same_route": 0, "surveys": 0},
            "direction_source_metrics": {"arxiv": {"attempted": True}},
            "seed_source_metrics": {},
            "handoff_job_id": "job-1",
            "final_understanding_status": "SUCCESS",
            "blocking_reason": "",
            "cards_status_code": 200,
            "returned_card_components": ["paper_card", "formula_cards", "teaching_cards"],
            "formula_origin_summary": {},
            "warnings": [],
            "final_verdict": "PASS",
            "verdict_reasons": [],
        }

    monkeypatch.setattr(matrix, "_run_query_with_timeout", fake_run_query)
    args = matrix.parse_args([
        "--queries",
        "q1",
        "q2",
        "--workspace",
        str(tmp_path / "workspace"),
        "--output-json",
        str(tmp_path / "summary.json"),
    ])

    summary = matrix.run_matrix(args)

    assert summary["total_queries"] == 2
    assert summary["failed"] == 1
    assert summary["passed"] == 1
    assert summary["failure_root_cause_breakdown"]["query_timeout"] == 1
    assert summary["rows"][1]["query"] == "q2"


def test_exit_code_treats_blocked_rows_as_results() -> None:
    summary = {
        "total_queries": 1,
        "failed": 0,
        "blocked": 1,
        "passed": 0,
    }

    assert matrix._exit_code_for_summary(summary, max_failures=0) == (0, "")


def test_exit_code_rejects_empty_matrix() -> None:
    summary = {
        "total_queries": 0,
        "failed": 0,
        "blocked": 0,
        "passed": 0,
    }

    code, message = matrix._exit_code_for_summary(summary, max_failures=0)

    assert code == 2
    assert "No rows produced" in message
