from __future__ import annotations

import os
from pathlib import Path

import httpx
from starlette.testclient import TestClient

from researchsensei.web.app import create_app


def _pdf_response(content: bytes = b"%PDF-1.4\nminimal") -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/pdf", "content-length": str(len(content))},
        content=content,
    )


def _source_status_artifact(client: TestClient, job_id: str) -> dict:
    old_debug = os.environ.get("SENSEI_DEBUG")
    os.environ["SENSEI_DEBUG"] = "1"
    try:
        response = client.get(f"/api/v1/jobs/{job_id}/artifacts")
        assert response.status_code == 200
        artifacts = response.json()["artifacts"]
        matches = [artifact for artifact in artifacts if artifact["artifact_type"] == "source_status"]
        assert matches
        return matches[0]
    finally:
        if old_debug is None:
            os.environ.pop("SENSEI_DEBUG", None)
        else:
            os.environ["SENSEI_DEBUG"] = old_debug


def test_parse_api_accepts_local_path_txt_and_writes_source_status(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "paper.txt"
    source.write_text("Abstract\nA local paper.", encoding="utf-8")
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", allowed_local_roots=[allowed]))

    response = client.post("/api/v1/documents/parse", data={"local_path": str(source)})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert any(artifact["artifact_type"] == "source_status" for artifact in data["artifacts"])
    source_status = _source_status_artifact(client, data["job_id"])["content"]
    assert source_status["source_type"] == "local_path"
    assert source_status["status"] == "resolved"


def test_parse_api_accepts_local_path_md(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "paper.md"
    source.write_text("# Paper\n## Abstract\nA local paper.", encoding="utf-8")
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", allowed_local_roots=[allowed]))

    response = client.post("/api/v1/documents/parse", data={"local_path": str(source)})

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_parse_api_rejects_local_path_outside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "secret.txt"
    source.write_text("secret", encoding="utf-8")
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", allowed_local_roots=[allowed]))

    response = client.post("/api/v1/documents/parse", data={"local_path": str(source)})

    assert response.status_code == 400
    assert response.json()["detail"]["source_status"]["warnings"] == ["SECURITY_REJECTED"]


def test_parse_api_rejects_local_path_traversal(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "secret.txt"
    source.write_text("secret", encoding="utf-8")
    traversal = allowed / ".." / "outside" / "secret.txt"
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", allowed_local_roots=[allowed]))

    response = client.post("/api/v1/documents/parse", data={"local_path": str(traversal)})

    assert response.status_code == 400
    assert response.json()["detail"]["source_status"]["warnings"] == ["SECURITY_REJECTED"]


def test_parse_api_accepts_mocked_pdf_url(tmp_path: Path) -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _pdf_response()

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=http_client))

    response = client.post("/api/v1/documents/parse", data={"pdf_url": "https://example.com/paper.pdf"})

    assert response.status_code == 200
    data = response.json()
    assert seen_urls == ["https://example.com/paper.pdf"]
    source_status = _source_status_artifact(client, data["job_id"])["content"]
    assert source_status["source_type"] == "pdf_url"
    assert source_status["content_type"] == "application/pdf"


def test_parse_api_accepts_arxiv_id_with_mocked_download(tmp_path: Path) -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _pdf_response()

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=http_client))

    response = client.post("/api/v1/documents/parse", data={"arxiv_id": "2301.12345"})

    assert response.status_code == 200
    data = response.json()
    assert seen_urls == ["https://arxiv.org/pdf/2301.12345.pdf"]
    source_status = _source_status_artifact(client, data["job_id"])["content"]
    assert source_status["source_type"] == "arxiv_id"


def test_parse_api_accepts_arxiv_abs_url_with_mocked_download(tmp_path: Path) -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: _pdf_response()))
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=http_client))

    response = client.post("/api/v1/documents/parse", data={"arxiv_url": "https://arxiv.org/abs/2301.12345"})

    assert response.status_code == 200
    data = response.json()
    source_status = _source_status_artifact(client, data["job_id"])["content"]
    assert source_status["source_type"] == "arxiv_url"


def test_parse_api_accepts_arxiv_pdf_url_with_mocked_download(tmp_path: Path) -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _pdf_response()

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", http_client=http_client))

    response = client.post("/api/v1/documents/parse", data={"arxiv_url": "https://arxiv.org/pdf/2301.12345.pdf"})

    assert response.status_code == 200
    assert seen_urls == ["https://arxiv.org/pdf/2301.12345.pdf"]
