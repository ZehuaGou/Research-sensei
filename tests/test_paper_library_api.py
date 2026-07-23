from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from researchsensei.web.app import create_app


def test_library_api_imports_manifest_and_deletes_paper(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    topic_dir = workspace / "literature_searches" / "time series anomaly detection"
    topic_dir.mkdir(parents=True)
    pdf = topic_dir / "Manifest Imported Paper.pdf"
    content = b"%PDF-1.4\nmanifest\n%%EOF"
    pdf.write_bytes(content)
    manifest = {
        "query": "time series anomaly detection",
        "papers": [
            {
                "paper_id": "paper-1",
                "title": "Manifest Imported Paper",
                "authors": ["A. Researcher"],
                "year": 2024,
                "venue": "AAAI",
                "venue_rank": "A*",
                "pdf_url": "https://example.test/paper.pdf",
                "landing_url": "https://example.test/paper",
                "local_path": str(pdf),
                "download_status": "downloaded",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
    }
    (topic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    client = TestClient(create_app(workspace_root=workspace))
    response = client.get("/api/v1/library/papers")

    assert response.status_code == 200
    papers = response.json()["papers"]
    assert len(papers) == 1
    assert response.json()["total"] == 1
    assert response.json()["limit"] == 100
    assert response.json()["offset"] == 0
    assert papers[0]["title"] == "Manifest Imported Paper"
    assert papers[0]["local_path"] == str(pdf.resolve())

    delete_response = client.delete(f"/api/v1/library/papers/{papers[0]['paper_id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "DELETED"
    assert not pdf.exists()

    empty_page = client.get("/api/v1/library/papers?limit=1&offset=1")
    assert empty_page.status_code == 200
    assert empty_page.json()["papers"] == []
