from __future__ import annotations

from typing import Any

from scripts.run_main_chain_smoke import evaluate_gating, run_main_chain_smoke


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
    ) -> None:
        self.final_status = final_status
        self.cards_status_code = cards_status_code
        self.cards_payload = cards_payload
        self.seed_status = seed_status
        self.seed_warnings = seed_warnings or []
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
        self.requests.append(("POST", url, json))
        if url == "/api/v1/directions/search":
            return FakeResponse({
                "status": "SUCCESS",
                "warnings": [],
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
                "upstream_papers": [
                    _seed_paper("2401.00002", "Foundation Paper", "upstream"),
                ],
                "downstream_papers": [
                    _seed_paper("2401.00003", "Follow-up Paper", "downstream"),
                ],
                "same_route_papers": [],
                "related_surveys": [],
            })
        if url == "/api/v1/directions/deep_read":
            return FakeResponse({"handoff_status": "JOB_CREATED", "job_id": "job-123"})
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
    assert result["selected_seed_handoff_arxiv_id"] == "2401.00002"
    assert result["seed_expansion_group_counts"] == {
        "upstream": 1,
        "downstream": 1,
        "same_route": 0,
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
