from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.direction.seed_expansion import SeedExpansionService
from researchsensei.schemas import CandidatePaper, VerificationStatus
from researchsensei.web.app import create_app


class StaticAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return [
            CandidatePaper(
                paper_id="2401.00002",
                title="Time Series Anomaly Detection Survey",
                authors=["A. Researcher"],
                year=2024,
                source="arxiv",
                sources=["arxiv"],
                url="https://arxiv.org/abs/2401.00002",
                landing_url="https://arxiv.org/abs/2401.00002",
                arxiv_id="2401.00002",
                pdf_url="https://arxiv.org/pdf/2401.00002.pdf",
                abstract="survey review time series anomaly detection",
                source_confidence="high",
            )
        ]


class EmptyAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return []


class StaticVerifier:
    def verify_batch(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        return [
            candidate.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFIED,
                    "verification_method": "fixture",
                    "verification_reason": "fixture-confirmed",
                    "verification_confidence": "high",
                }
            )
            for candidate in candidates
        ]


def _client(tmp_path: Path, adapter: object) -> TestClient:
    service = SeedExpansionService(
        adapters={"arxiv": adapter},  # type: ignore[arg-type]
        sources=["arxiv"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        max_results_per_source=2,
        max_group_items=3,
    )
    return TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            seed_expansion_service=service,
        )
    )


def test_seed_expansion_api_returns_bundle(tmp_path: Path) -> None:
    client = _client(tmp_path, StaticAdapter())

    response = client.post(
        "/api/v1/directions/seed_expansion",
        json={"seed": {"title": "Time Series Anomaly Detection", "arxiv_id": "2401.00001"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["seed_expansion_status"] == "SUCCESS"
    assert data["papers"]
    assert data["papers"][0]["can_enter_analysis"] is True
    assert data["papers"][0]["citation_graph_verified"] is False


def test_seed_expansion_api_empty_result_is_explicit(tmp_path: Path) -> None:
    client = _client(tmp_path, EmptyAdapter())

    response = client.post(
        "/api/v1/directions/seed_expansion",
        json={"seed": {"title": "No Results Seed"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EMPTY_RESULT"
    assert data["papers"] == []


def test_seed_expansion_api_rejects_non_object_seed(tmp_path: Path) -> None:
    client = _client(tmp_path, StaticAdapter())

    response = client.post("/api/v1/directions/seed_expansion", json={"seed": "not-an-object"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
