from __future__ import annotations

from typing import Any

from scripts.run_main_chain_smoke import _handoff_payload, _select_handoff_candidate, evaluate_gating, run_main_chain_smoke


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeClient:
    def __init__(
        self,
        *,
        final_status: str,
        cards_status_code: int,
        cards_payload: dict[str, Any],
        seed_status: str = "SUCCESS",
        seed_warnings: list[str] | None = None,
        handoff_failure: dict[str, Any] | None = None,
    ) -> None:
        self.final_status = final_status
        self.cards_status_code = cards_status_code
        self.cards_payload = cards_payload
        self.seed_status = seed_status
        self.seed_warnings = seed_warnings or []
        self.handoff_failure = handoff_failure
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
        self.requests.append(("POST", url, json))
        if url == "/api/v1/directions/search":
            return FakeResponse({
                "status": "SUCCESS",
                "warnings": [],
                "source_metrics": [
                    {"source": "arxiv", "attempted": True, "success": True, "count": 1, "latency_ms": 10, "error": ""},
                    {"source": "openalex", "attempted": True, "success": True, "count": 1, "latency_ms": 11, "error": ""},
                    {"source": "semantic_scholar", "attempted": True, "success": True, "count": 0, "latency_ms": 12, "error": ""},
                    {"source": "crossref", "attempted": True, "success": True, "count": 0, "latency_ms": 13, "error": ""},
                ],
                "papers": [
                    {
                        "paper_id": "p1",
                        "title": "Metadata Only Candidate",
                        "source": "crossref",
                    },
                    {
                        "paper_id": "2401.00001",
                        "title": "Time Series Anomaly Detection with Transformers",
                        "source": "arxiv",
                        "sources": ["arxiv", "openalex"],
                        "arxiv_id": "2401.00001",
                        "arxiv_url": "https://arxiv.org/abs/2401.00001",
                        "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
                    },
                ],
            })
        if url == "/api/v1/directions/seed_expansion":
            return FakeResponse({
                "status": self.seed_status,
                "seed_expansion_status": self.seed_status,
                "warnings": self.seed_warnings,
                "source_metrics": [
                    {"relation_type": "same_route", "source": "arxiv", "attempted": True, "success": True, "count": 1, "latency_ms": 20, "error": ""},
                    {"relation_type": "same_route", "source": "openalex", "attempted": True, "success": False, "count": 0, "latency_ms": 21, "error": "rate limited"},
                ],
                "upstream_papers": [
                    _seed_paper("2401.00002", "Foundation Paper", "upstream"),
                ],
                "downstream_papers": [
                    _seed_paper("2401.00003", "Follow-up Method Paper", "downstream"),
                ],
                "same_route_papers": [
                    _seed_paper("2401.00004", "Neural Architecture for Time Series Anomaly Detection", "same_route"),
                ],
                "related_surveys": [],
            })
        if url == "/api/v1/directions/deep_read":
            if self.handoff_failure is not None:
                return FakeResponse({"detail": self.handoff_failure}, status_code=400)
            return FakeResponse({
                "handoff_status": "JOB_CREATED",
                "job_id": "job-123",
                "source_status": {
                    "source_type": "arxiv_source",
                    "source_strategy": "source_first",
                    "preferred_m2_input": "latex_source",
                    "latex_source_available": True,
                },
            })
        raise AssertionError(f"unexpected POST {url}")

    def get(self, url: str) -> FakeResponse:
        self.requests.append(("GET", url, None))
        if url == "/api/v1/jobs/job-123/understanding_status":
            return FakeResponse({
                "job_id": "job-123",
                "understanding_status": {
                    "status": self.final_status,
                    "blocking_reason": "FORMULA_DERIVATION_BLOCKED" if self.final_status == "DEGRADED_STRUCTURAL" else "",
                    "component_status": {
                        "paper_card": "SUCCESS" if self.final_status in {"SUCCESS", "DEGRADED_STRUCTURAL"} else "BASELINE",
                        "formula_cards": "SUCCESS" if self.final_status == "SUCCESS" else "FAILED",
                        "teaching_cards": "SUCCESS" if self.final_status in {"SUCCESS", "DEGRADED_STRUCTURAL"} else "BASELINE",
                    },
                },
                "paper_workspace_status": {
                    "formula_origin": "source_latex",
                    "formula_ocr_status": "not_required",
                },
            })
        if url == "/api/v1/jobs/job-123/cards":
            return FakeResponse(self.cards_payload, self.cards_status_code)
        raise AssertionError(f"unexpected GET {url}")


def _seed_paper(arxiv_id: str, title: str, relation_type: str) -> dict[str, Any]:
    return {
        "paper_id": arxiv_id,
        "title": title,
        "source": "arxiv",
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        "relation_type": relation_type,
        "can_enter_m2": True,
        "can_prepare_deep_read": True,
    }


def test_main_chain_smoke_success_cards_gate() -> None:
    client = FakeClient(
        final_status="SUCCESS",
        cards_status_code=200,
        cards_payload={"cards": {"paper_card": {}, "formula_cards": {}, "teaching_cards": {}}},
    )

    result = run_main_chain_smoke(
        client,
        query="time series anomaly detection",
        max_candidates=5,
        llm_enabled=True,
        llm_mode_note="LLM enabled with provider 'mimo'.",
    )

    assert result["final_verdict"] == "PASS"
    assert result["selected_candidate_arxiv_id"] == "2401.00001"
    assert result["selected_candidate_sources"] == ["arxiv", "openalex"]
    assert result["selected_seed_handoff_arxiv_id"] == "2401.00004"
    assert result["selected_input_type"] == "arxiv_source"
    assert result["source_strategy"] == "source_first"
    assert result["arxiv_source_downloaded"] is True
    assert result["direction_source_metrics"]["arxiv"]["count"] == 1
    assert result["seed_source_metrics"]["openalex"]["failure_count"] == 1
    assert result["formula_origin_summary"]["origins"] == "source_latex"
    assert result["seed_expansion_group_counts"] == {
        "upstream": 1,
        "downstream": 1,
        "same_route": 1,
        "surveys": 0,
    }
    assert result["returned_card_components"] == ["formula_cards", "paper_card", "teaching_cards"]


def test_main_chain_smoke_degraded_cards_gate_only_success_components() -> None:
    client = FakeClient(
        final_status="DEGRADED_STRUCTURAL",
        cards_status_code=200,
        cards_payload={"cards": {"paper_card": {}, "teaching_cards": {}}, "missing_components": ["formula_cards"]},
        seed_status="DEGRADED",
        seed_warnings=["SEED_SOURCE_FAILED:survey:semantic_scholar: RuntimeError: rate limited"],
    )

    result = run_main_chain_smoke(
        client,
        query="time series anomaly detection",
        max_candidates=5,
        llm_enabled=True,
    )

    assert result["final_verdict"] == "DEGRADED_PASS"
    assert result["final_understanding_status"] == "DEGRADED_STRUCTURAL"
    assert result["cards_status_code"] == 200
    assert "formula_cards" not in result["returned_card_components"]
    assert any("SEED_SOURCE_FAILED" in warning for warning in result["warnings"])


def test_main_chain_smoke_prefers_method_like_candidate_over_foundation() -> None:
    client = FakeClient(
        final_status="DEGRADED_STRUCTURAL",
        cards_status_code=200,
        cards_payload={"cards": {"paper_card": {}, "teaching_cards": {}}},
    )

    result = run_main_chain_smoke(
        client,
        query="time series anomaly detection",
        max_candidates=5,
        llm_enabled=True,
    )

    assert result["selected_seed_handoff_title"] == "Neural Architecture for Time Series Anomaly Detection"
    assert result["selected_seed_handoff_arxiv_id"] == "2401.00004"


def test_handoff_candidate_selection_rejects_unrelated_source_backed_paper() -> None:
    candidate = _select_handoff_candidate(
        [
            _seed_paper("1411.4413", "Observation of a rare particle decay", "same_route"),
        ],
        query="graph anomaly detection",
    )

    assert candidate is None


def test_main_chain_smoke_blocked_cards_gate() -> None:
    client = FakeClient(
        final_status="BLOCKED_UNDERSTANDING",
        cards_status_code=403,
        cards_payload={"detail": {"status": "BLOCKED_UNDERSTANDING"}},
    )

    result = run_main_chain_smoke(
        client,
        query="time series anomaly detection",
        max_candidates=5,
        llm_enabled=True,
    )

    assert result["final_verdict"] == "DEGRADED_PASS"
    assert result["cards_status_code"] == 403


def test_main_chain_smoke_handoff_failure_returns_fail_summary() -> None:
    client = FakeClient(
        final_status="",
        cards_status_code=0,
        cards_payload={},
        handoff_failure={
            "status": "PDF_DOWNLOAD_FAILED",
            "job_id": "failed-job",
            "message": "PDF download failed for the direction candidate.",
            "source_status": {"source_type": "pdf_url"},
        },
    )

    result = run_main_chain_smoke(
        client,
        query="multivariate time series imputation",
        max_candidates=5,
        llm_enabled=True,
    )

    assert result["final_verdict"] == "FAIL"
    assert result["handoff_job_id"] == "failed-job"
    assert result["selected_input_type"] == "external_pdf"
    assert result["message"] == "PDF download failed for the direction candidate."


def test_main_chain_smoke_no_llm_baseline_is_degraded_pass() -> None:
    client = FakeClient(
        final_status="BASELINE_ONLY",
        cards_status_code=403,
        cards_payload={"detail": {"status": "BASELINE_ONLY"}},
    )

    result = run_main_chain_smoke(
        client,
        query="time series anomaly detection",
        max_candidates=5,
        llm_enabled=False,
        llm_mode_note="MIMO_API_KEY is missing; running no-LLM smoke and expecting BASELINE_ONLY.",
    )

    assert result["final_verdict"] == "DEGRADED_PASS"
    assert result["llm_enabled"] is False
    assert result["final_understanding_status"] == "BASELINE_ONLY"


def test_llm_enabled_baseline_only_fails() -> None:
    verdict, reasons = evaluate_gating(
        final_status="BASELINE_ONLY",
        cards_status_code=403,
        returned_components=[],
        understanding_status={"component_status": {"paper_card": "BASELINE"}},
        llm_enabled=True,
    )

    assert verdict == "FAIL"
    assert "LLM was enabled" in reasons[0]


def test_handoff_payload_drops_unsupported_old_arxiv_id_when_pdf_exists() -> None:
    payload = _handoff_payload({
        "title": "Old arXiv paper",
        "arxiv_id": "9807001",
        "pdf_url": "https://example.test/paper.pdf",
    })

    assert payload["arxiv_id"] == ""
    assert payload["pdf_url"] == "https://example.test/paper.pdf"
