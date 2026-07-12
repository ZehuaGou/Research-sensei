from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


UPLOAD_CHUNK_BYTES = 1024 * 1024
SUPPORTED_UPLOAD_SUFFIXES = {".md", ".txt", ".pdf", ".tex"}
_ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".tex": {"application/x-tex", "text/x-tex", "text/plain", "application/octet-stream"},
}


class UploadValidationError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class SavedUpload:
    path: Path
    original_filename: str
    content_type: str
    size_bytes: int


class UploadService:
    def __init__(
        self,
        incoming_dir: str | Path,
        *,
        max_bytes: int,
        chunk_bytes: int = UPLOAD_CHUNK_BYTES,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if chunk_bytes <= 0:
            raise ValueError("chunk_bytes must be positive")
        self.incoming_dir = Path(incoming_dir)
        self.max_bytes = int(max_bytes)
        self.chunk_bytes = int(chunk_bytes)

    async def save(self, upload: UploadFile) -> SavedUpload:
        original_filename = str(upload.filename or "")
        suffix = Path(original_filename).suffix.lower()
        if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
            raise UploadValidationError(
                "UNSUPPORTED_FILE_TYPE",
                f"Unsupported file type: {suffix or '<none>'}",
            )
        content_type = str(upload.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_MIME_TYPES[suffix]:
            raise UploadValidationError(
                "UPLOAD_MIME_MISMATCH",
                f"Content type {content_type or '<none>'} is not valid for {suffix} uploads.",
            )

        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        temp_path = self.incoming_dir / f".upload-{token}.tmp"
        final_path = self.incoming_dir / f"{token}{suffix}"
        total = 0
        prefix = bytearray()
        try:
            with temp_path.open("xb") as handle:
                while True:
                    chunk = await upload.read(self.chunk_bytes)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise UploadValidationError(
                            "UPLOAD_TOO_LARGE",
                            f"Upload exceeds the {self.max_bytes}-byte limit.",
                            status_code=413,
                        )
                    if len(prefix) < 4096:
                        prefix.extend(chunk[: 4096 - len(prefix)])
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if total == 0:
                raise UploadValidationError("UPLOAD_EMPTY", "Uploaded file is empty.")
            _validate_signature(suffix, bytes(prefix))
            os.replace(temp_path, final_path)
            return SavedUpload(
                path=final_path,
                original_filename=original_filename,
                content_type=content_type,
                size_bytes=total,
            )
        except BaseException:
            temp_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @staticmethod
    def cleanup(saved: SavedUpload | Path | None) -> None:
        path = saved.path if isinstance(saved, SavedUpload) else saved
        if path is not None:
            Path(path).unlink(missing_ok=True)


def _validate_signature(suffix: str, prefix: bytes) -> None:
    if suffix == ".pdf":
        if not prefix.startswith(b"%PDF-"):
            raise UploadValidationError(
                "UPLOAD_SIGNATURE_MISMATCH",
                "The uploaded .pdf file does not have a PDF signature.",
            )
        return
    if b"\x00" in prefix:
        raise UploadValidationError(
            "UPLOAD_SIGNATURE_MISMATCH",
            f"The uploaded {suffix} file contains binary data.",
        )
    try:
        prefix.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UploadValidationError(
            "UPLOAD_SIGNATURE_MISMATCH",
            f"The uploaded {suffix} file is not valid UTF-8 text.",
        ) from error
