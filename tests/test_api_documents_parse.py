from __future__ import annotations

from pathlib import Path
import sqlite3

from starlette.testclient import TestClient

from researchsensei.core.config import ConfigService
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


def test_parse_upload_reuses_existing_job_for_same_content(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    payload = b"# Paper\n## Abstract\nWe study anomaly detection."

    first = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.md", payload, "text/markdown")},
    )
    second = client.post(
        "/api/v1/documents/parse",
        files={"file": ("renamed.md", payload, "text/markdown")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert second_data["status"] == "JOB_REUSED"
    assert second_data["cache_hit"] is True
    assert second_data["job_id"] == first_data["job_id"]
    assert second_data["source_identity"] == first_data["source_identity"]


def test_parse_local_path_reuses_existing_job_by_file_hash(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    source = workspace / "paper.md"
    source.write_text("# Paper\n## Abstract\nA local cache test.", encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    first = client.post("/api/v1/documents/parse", data={"local_path": str(source)})
    second = client.post("/api/v1/documents/parse", data={"local_path": str(source)})

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert second_data["status"] == "JOB_REUSED"
    assert second_data["cache_hit"] is True
    assert second_data["job_id"] == first_data["job_id"]
    assert second_data["source_identity"] == first_data["source_identity"]
    recent = client.get("/api/v1/jobs").json()["jobs"]
    assert [job["job_id"] for job in recent].count(first_data["job_id"]) == 1


def test_parse_local_path_force_creates_new_job(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    source = workspace / "paper.md"
    source.write_text("# Paper\n## Abstract\nA local force parse test.", encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    first = client.post("/api/v1/documents/parse", data={"local_path": str(source)})
    forced = client.post("/api/v1/documents/parse", data={"local_path": str(source), "force": "true"})

    assert first.status_code == 200
    assert forced.status_code == 200
    forced_data = forced.json()
    assert forced_data.get("cache_hit") is not True
    assert forced_data["job_id"] != first.json()["job_id"]


def test_reparse_job_creates_new_job_from_existing_source(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    source = workspace / "paper.md"
    source.write_text("# Paper\n## Abstract\nA reparse test.", encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    first = client.post("/api/v1/documents/parse", data={"local_path": str(source)})
    assert first.status_code == 200
    first_data = first.json()

    reparsed = client.post(f"/api/v1/jobs/{first_data['job_id']}/reparse")

    assert reparsed.status_code == 200
    reparsed_data = reparsed.json()
    assert reparsed_data["status"] == "JOB_CREATED"
    assert reparsed_data["source_job_id"] == first_data["job_id"]
    assert reparsed_data["job_id"] != first_data["job_id"]

    old_status = client.get(f"/api/v1/jobs/{first_data['job_id']}/understanding_status")
    assert old_status.status_code == 200
    assert old_status.json()["job_id"] == reparsed_data["job_id"]

    # Simulate a database created before successor links were persisted.
    db_path = workspace / "sensei.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("delete from job_successors")
    restarted = TestClient(create_app(workspace_root=workspace))
    recovered = restarted.get(f"/api/v1/jobs/{first_data['job_id']}/understanding_status")
    assert recovered.status_code == 200
    assert recovered.json()["job_id"] == reparsed_data["job_id"]


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
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_parse_doi_resolves_legal_oa_pdf_and_creates_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.org")
    http_client = UnpaywallOaHttpClient(_sample_pdf_bytes())
    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
        config_service=_isolated_config(tmp_path),
    ))

    response = client.post(
        "/api/v1/documents/parse",
        data={"title": "Example Paper", "doi": "10.1145/example"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert data["status"] == "succeeded"
    job = client.get(f"/api/v1/jobs/{data['job_id']}").json()
    assert any(artifact["artifact_type"] == "source_status" for artifact in job["artifacts"])
    assert any("api.unpaywall.org" in url for url in http_client.urls)


def test_parse_doi_reuses_existing_job_before_unpaywall_lookup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.org")
    http_client = UnpaywallOaHttpClient(_sample_pdf_bytes())
    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        http_client=http_client,
        config_service=_isolated_config(tmp_path),
    ))

    first = client.post(
        "/api/v1/documents/parse",
        data={"title": "Example Paper", "doi": "10.1145/example"},
    )
    http_client.urls.clear()
    second = client.post(
        "/api/v1/documents/parse",
        data={"title": "Example Paper", "doi": "10.1145/EXAMPLE"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "JOB_REUSED"
    assert second.json()["cache_hit"] is True
    assert second.json()["job_id"] == first.json()["job_id"]
    assert http_client.urls == []


def test_parse_doi_without_oa_pdf_returns_source_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.org")
    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        http_client=UnpaywallNotFoundHttpClient(),
        config_service=_isolated_config(tmp_path),
    ))

    response = client.post(
        "/api/v1/documents/parse",
        data={"title": "Example Paper", "doi": "10.1145/example"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["job_id"]
    assert detail["status"] == "NO_LEGAL_OA_FULLTEXT_FOUND"
    assert detail["source_status"]["source_type"] == "doi"
    assert detail["source_status"]["status"] == "rejected"
    assert "UNPAYWALL_NOT_FOUND" in detail["source_status"]["warnings"]


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


def test_delete_job_removes_it_from_recent_jobs(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    created = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.md", b"# Paper\n## Abstract\nA tiny paper.", "text/markdown")},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    deleted = client.delete(f"/api/v1/jobs/{job_id}")

    assert deleted.status_code == 200
    assert deleted.json()["status"] == "DELETED"
    assert deleted.json()["job_id"] == job_id
    assert deleted.json()["artifacts_removed"] is True
    assert deleted.json()["cleanup_warning"] == ""
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404
    recent = client.get("/api/v1/jobs").json()["jobs"]
    assert all(job["job_id"] != job_id for job in recent)


class StubHttpResponse:
    def __init__(
        self,
        content: bytes,
        *,
        content_type: str = "application/pdf",
        url: str = "https://repo.example.org/paper.pdf",
    ) -> None:
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.url = url
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None


class UnpaywallOaHttpClient:
    def __init__(self, pdf_content: bytes) -> None:
        self.pdf_content = pdf_content
        self.urls: list[str] = []

    def get(self, url: str, **kwargs):
        self.urls.append(url)
        if "api.unpaywall.org" in url:
            return UnpaywallResponse(pdf_url="https://repo.example.org/paper.pdf")
        return StubHttpResponse(self.pdf_content, url=url)


class UnpaywallNotFoundHttpClient:
    def get(self, url: str, **kwargs):
        if "api.unpaywall.org" in url:
            response = StubHttpResponse(b"not found")
            response.status_code = 404
            return response
        return StubHttpResponse(b"", url=url)


class UnpaywallResponse:
    def __init__(self, pdf_url: str = "") -> None:
        self.status_code = 200
        location = {"url_for_pdf": pdf_url} if pdf_url else {}
        self._data = {
            "best_oa_location": location if location else None,
            "oa_locations": [location] if location else [],
        }

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


def _sample_pdf_bytes() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        (
            "Example Paper\n\n"
            "Abstract\n"
            "We study anomaly detection.\n\n"
            "Method\n"
            "Our method uses attention and reconstruction losses.\n\n"
            "Experiments\n"
            "We report benchmark results."
        ),
    )
    data = doc.tobytes()
    doc.close()
    return data


def _isolated_config(tmp_path: Path) -> ConfigService:
    return ConfigService(
        config_path=tmp_path / "missing.toml",
        env_path=tmp_path / "missing.env",
    )
