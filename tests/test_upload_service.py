from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers
from starlette.testclient import TestClient

from researchsensei.web.app import create_app
from researchsensei.web.services.upload_service import UploadService, UploadValidationError


def _upload(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_stream_upload_uses_generated_name_and_validates_text(tmp_path: Path) -> None:
    service = UploadService(tmp_path, max_bytes=1024, chunk_bytes=4)

    saved = await service.save(_upload("../../user-paper.md", b"# Paper\nvalid UTF-8", "text/markdown"))

    assert saved.path.parent == tmp_path
    assert saved.path.name != "user-paper.md"
    assert "user-paper" not in saved.path.name
    assert saved.path.read_bytes() == b"# Paper\nvalid UTF-8"


@pytest.mark.asyncio
async def test_stream_upload_rejects_empty_file_and_removes_temp(tmp_path: Path) -> None:
    service = UploadService(tmp_path, max_bytes=1024)

    with pytest.raises(UploadValidationError, match="empty") as excinfo:
        await service.save(_upload("empty.txt", b"", "text/plain"))

    assert excinfo.value.code == "UPLOAD_EMPTY"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_stream_upload_rejects_fake_pdf_signature(tmp_path: Path) -> None:
    service = UploadService(tmp_path, max_bytes=1024)

    with pytest.raises(UploadValidationError) as excinfo:
        await service.save(_upload("fake.pdf", b"not a pdf", "application/pdf"))

    assert excinfo.value.code == "UPLOAD_SIGNATURE_MISMATCH"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_stream_upload_stops_at_limit_and_removes_temp(tmp_path: Path) -> None:
    service = UploadService(tmp_path, max_bytes=8, chunk_bytes=4)

    with pytest.raises(UploadValidationError) as excinfo:
        await service.save(_upload("large.txt", b"0123456789", "text/plain"))

    assert excinfo.value.code == "UPLOAD_TOO_LARGE"
    assert list(tmp_path.iterdir()) == []


class InterruptedUpload:
    filename = "paper.txt"
    content_type = "text/plain"

    def __init__(self) -> None:
        self.calls = 0

    async def read(self, _size: int) -> bytes:
        self.calls += 1
        if self.calls == 1:
            return b"partial"
        raise RuntimeError("client disconnected")

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_stream_upload_interruption_removes_temp(tmp_path: Path) -> None:
    service = UploadService(tmp_path, max_bytes=1024, chunk_bytes=4)

    with pytest.raises(RuntimeError, match="disconnected"):
        await service.save(cast(UploadFile, InterruptedUpload()))

    assert list(tmp_path.iterdir()) == []


def test_upload_limit_is_enforced_by_api_without_leaking_temp_file(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    client = TestClient(create_app(workspace_root=workspace, max_download_bytes=8))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("large.txt", b"0123456789", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"
    incoming = workspace / "incoming"
    assert not incoming.exists() or list(incoming.iterdir()) == []
