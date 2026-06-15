from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.web.app import create_app


class StubHttpResponse:
    def __init__(
        self,
        content: bytes,
        *,
        content_type: str = "application/pdf",
        url: str = "https://arxiv.org/pdf/2401.00001.pdf",
    ) -> None:
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.url = url

    def raise_for_status(self) -> None:
        return None


class PdfHttpClient:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.urls: list[str] = []

    def get(self, url: str, **kwargs) -> StubHttpResponse:
        self.urls.append(url)
        return StubHttpResponse(self.content, url=url)


class FailingHttpClient:
    def get(self, url: str, **kwargs) -> StubHttpResponse:
        raise RuntimeError("network unavailable")


def test_direction_arxiv_candidate_handoff_creates_job(tmp_path: Path) -> None:
    http_client = PdfHttpClient(_sample_pdf_bytes())
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=http_client))

    response = client.post(
        "/api/v1/directions/deep_read",
        json={
            "candidate": {
                "title": "Time Series Anomaly Detection with Transformers",
                "arxiv_id": "2401.00001",
                "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["handoff_status"] == "JOB_CREATED"
    assert data["job_id"]
    assert data["source_status"]["source_type"] == "arxiv_id"
    assert data["understanding_status"]["status"] == "BASELINE_ONLY"
    assert http_client.urls == ["https://arxiv.org/pdf/2401.00001.pdf"]

    status_response = client.get(f"/api/v1/jobs/{data['job_id']}/understanding_status")
    assert status_response.status_code == 200


def test_direction_handoff_source_unavailable_returns_explicit_failure(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/directions/deep_read",
        json={"candidate": {"title": "Metadata Only Candidate"}},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["status"] == "SOURCE_UNAVAILABLE"
    assert detail["source_status"]["status"] == "rejected"


def test_direction_handoff_doi_returns_not_implemented(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/directions/deep_read",
        json={"candidate": {"title": "DOI Candidate", "doi": "10.1145/example"}},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["status"] == "DOI_NOT_IMPLEMENTED"
    assert detail["source_status"]["source_type"] == "doi"
    assert "DOI_NOT_IMPLEMENTED" in detail["source_status"]["warnings"]


def test_direction_handoff_pdf_download_failure_is_explicit(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=FailingHttpClient()))

    response = client.post(
        "/api/v1/directions/deep_read",
        json={"candidate": {"title": "PDF Candidate", "pdf_url": "https://example.test/paper.pdf"}},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["status"] == "PDF_DOWNLOAD_FAILED"
    assert detail["source_status"]["source_type"] == "pdf_url"


def test_direction_fake_candidate_does_not_generate_success_job(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/directions/deep_read",
        json={"candidate": {"title": "Fake Candidate", "url": "https://example.test/metadata-only"}},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["status"] == "SOURCE_UNAVAILABLE"
    job_response = client.get(f"/api/v1/jobs/{detail['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "failed"


def test_direction_handoff_preserves_cards_gating(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            http_client=PdfHttpClient(_sample_pdf_bytes()),
        )
    )

    response = client.post(
        "/api/v1/directions/deep_read",
        json={"candidate": {"title": "Arxiv Candidate", "arxiv_url": "https://arxiv.org/abs/2401.00001"}},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")

    assert cards_response.status_code == 403
    assert cards_response.json()["detail"]["status"] == "BASELINE_ONLY"


def _sample_pdf_bytes() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        (
            "Time Series Anomaly Detection with Transformers\n\n"
            "Abstract\n"
            "We study anomaly detection for multivariate time series.\n\n"
            "Method\n"
            "Our method uses attention and reconstruction losses.\n\n"
            "Experiments\n"
            "We evaluate on benchmark datasets and report strong F1."
        ),
    )
    data = doc.tobytes()
    doc.close()
    return data
