from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.web.app import create_app


def test_parse_upload_markdown_creates_job_and_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.md", b"# Paper\n## Abstract\nWe study anomaly detection.", "text/markdown")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert data["status"] == "succeeded"
    assert data["degraded"] is False
    assert data["artifacts"][0]["artifact_type"] == "ingestion"
    assert Path(data["artifacts"][0]["path"]).exists()
    assert isinstance(data["warnings"], list)


def test_parse_upload_markdown_generates_phase6_artifacts(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={
            "file": (
                "paper.md",
                b"# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe minimize L = L_rec.\n\n## Experiments\nTable 1 reports F1.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 200
    artifacts = response.json()["artifacts"]
    artifact_types = {artifact["artifact_type"] for artifact in artifacts}

    assert {"source_status", "ingestion", "passage_index", "claim_evidence", "evidence_index", "paper_skeleton", "paper_card", "formula_cards", "teaching_cards", "understanding_status", "quality_report"} == artifact_types
    assert all(Path(artifact["path"]).exists() for artifact in artifacts)


def test_parse_upload_txt_creates_job_and_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.txt", b"Abstract\nA tiny paper.", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert data["status"] == "succeeded"
    assert data["artifacts"][0]["artifact_type"] == "ingestion"


def test_parse_upload_rejects_unsupported_file_type(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type: .exe"


def test_parse_doi_returns_not_implemented_source_status(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        data={"title": "Example Paper", "doi": "10.1145/example"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["job_id"]
    assert detail["source_status"]["source_type"] == "doi"
    assert detail["source_status"]["status"] == "rejected"
    assert "DOI_NOT_IMPLEMENTED" in detail["source_status"]["warnings"]


def test_direction_endpoint_returns_minimal_bundle_and_seed_expansion_is_wired(tmp_path: Path) -> None:
    from researchsensei.schemas import CandidatePool, DirectionBundle, QueryPlan, ReadingPlan
    from researchsensei.direction.seed_expansion import SeedExpansionService

    class StubDirectionService:
        def explore(self, query: str) -> DirectionBundle:
            return DirectionBundle(
                status="SUCCESS",
                direction_workspace_status="SUCCESS",
                query=query,
                message="fixture",
                overview="fixture overview",
                query_plan=QueryPlan(user_query=query, english_query=query),
                candidate_pool=CandidatePool(query=query),
                filtered_candidates=CandidatePool(query=query),
                reading_plan=ReadingPlan(topic=query),
            )

    class EmptySeedAdapter:
        def search(self, query: str, max_results: int = 20) -> list:
            return []

    seed_service = SeedExpansionService(
        adapters={"arxiv": EmptySeedAdapter()},  # type: ignore[arg-type]
        sources=["arxiv"],
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            direction_service=StubDirectionService(),  # type: ignore[arg-type]
            seed_expansion_service=seed_service,
        )
    )

    direction = client.post("/api/v1/directions/search", json={"query": "time series anomaly detection"})
    seed = client.post("/api/v1/directions/seed_expansion", json={"seed": {"title": "time series anomaly detection"}})

    assert direction.status_code == 200
    assert direction.json()["direction_workspace_status"] == "SUCCESS"
    assert direction.json()["overview"] == "fixture overview"
    assert direction.json()["papers"] == []
    assert seed.status_code == 200
    assert seed.json()["seed_expansion_status"] == "EMPTY_RESULT"
    assert seed.json()["papers"] == []


def test_health_endpoint_is_preserved(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "researchsensei"}
