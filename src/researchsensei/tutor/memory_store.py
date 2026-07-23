from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.tutor import TutorMemoryBundle, TutorMemoryRecord


MEMORY_FILENAME = "tutor_memory.json"
MAX_RECORDS = 200
MAX_BYTES = 1_048_576

_MEMORY_LOCK = threading.RLock()


class TutorMemoryStore:
    """Small atomic conversation ledger for one paper job.

    OpenCode owns conversational context.  This file only keeps the user-visible
    transcript metadata needed after a browser refresh; it is never treated as
    paper evidence.
    """

    def __init__(self, run_dir: Path, job_id: str) -> None:
        self.job_id = job_id
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / MEMORY_FILENAME
        # Memory files are tiny and writes are infrequent. A process-wide lock
        # is intentionally simpler and avoids path-identity races while a run
        # directory is being created concurrently on Windows.
        self._lock = _MEMORY_LOCK

    def read(self) -> TutorMemoryBundle:
        with self._lock:
            source_path = self.path if self.path.exists() else self._legacy_path()
            if source_path is None:
                return TutorMemoryBundle(job_id=self.job_id)
            try:
                value = json.loads(source_path.read_text(encoding="utf-8"))
                schema_version = str(value.get("schema_version") or "legacy")
                migrated = source_path != self.path or schema_version != "tutor_memory.v1"
                if migrated:
                    value["schema_version"] = "tutor_memory.v1"
                    value["migrated_from"] = schema_version
                    warnings = value.get("warnings")
                    warnings = warnings if isinstance(warnings, list) else []
                    value["warnings"] = [
                        *warnings,
                        {
                            "code": "TUTOR_MEMORY_SCHEMA_MIGRATED",
                            "message": "Legacy tutor memory was loaded and upgraded to the semantic schema.",
                        },
                    ]
                bundle = TutorMemoryBundle.model_validate(value)
                if bundle.job_id != self.job_id:
                    raise ValueError("memory job id does not match")
                if source_path != self.path:
                    self._write(bundle)
                    source_path.unlink(missing_ok=True)
                return bundle
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                preserved = source_path.with_name(
                    f"tutor_memory.corrupt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.json"
                )
                try:
                    os.replace(source_path, preserved)
                except OSError:
                    preserved = source_path
                return TutorMemoryBundle(
                    job_id=self.job_id,
                    warnings=[
                        WarningItem(
                            code="TUTOR_MEMORY_CORRUPTED",
                            message="Invalid tutor memory was preserved and excluded from the conversation.",
                            detail=f"{str(exc)[:220]}; preserved={preserved.name}",
                        )
                    ],
                )

    def _legacy_path(self) -> Path | None:
        candidates = sorted(
            path
            for path in self.run_dir.glob("*_memory.json")
            if path.name != MEMORY_FILENAME
        )
        return candidates[0] if candidates else None

    def clear(self) -> TutorMemoryBundle:
        with self._lock:
            bundle = TutorMemoryBundle(job_id=self.job_id)
            self._write(bundle)
            return bundle

    def append(
        self,
        *,
        memory_type: str,
        question: str,
        answer: str,
        evidence_refs: list[str],
        source_artifact: str,
        text: str = "",
        confidence: float = 0.8,
        metadata: dict[str, object] | None = None,
    ) -> TutorMemoryRecord:
        with self._lock:
            bundle = self.read()
            now = datetime.now(timezone.utc).isoformat()
            record = TutorMemoryRecord(
                memory_id=f"tutor-{uuid.uuid4().hex[:12]}",
                job_id=self.job_id,
                memory_type=memory_type,
                text=text,
                question=question,
                answer=answer,
                source_artifact=source_artifact,
                evidence_refs=list(dict.fromkeys(ref for ref in evidence_refs if ref)),
                confidence=max(0.0, min(1.0, confidence)),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            if not _is_useful(record):
                cleaned = _warning_once(
                    bundle.warnings,
                    "TUTOR_MEMORY_RECORDS_CLEANED",
                    "Blank, duplicate or internal-artifact memory records were removed.",
                )
                self._write(bundle.model_copy(update={"warnings": cleaned}))
                return record

            records = [
                item for item in bundle.records
                if _is_useful(item) and _dedupe_key(item) != _dedupe_key(record)
            ]
            warnings = list(bundle.warnings)
            if len(records) != len(bundle.records):
                warnings = _warning_once(
                    warnings,
                    "TUTOR_MEMORY_RECORDS_CLEANED",
                    "Blank, duplicate or internal-artifact memory records were removed.",
                )
            records.append(record)
            if len(records) > MAX_RECORDS:
                records = records[-MAX_RECORDS:]
                warnings = _warning_once(
                    warnings,
                    "TUTOR_MEMORY_RECORD_LIMIT",
                    "Old conversation records were removed to keep memory bounded.",
                )
            candidate = bundle.model_copy(update={"records": records, "warnings": warnings})
            size_trimmed = False
            while len(_encoded(candidate)) > MAX_BYTES and records:
                records.pop(0)
                candidate = candidate.model_copy(update={"records": list(records)})
                size_trimmed = True
            if size_trimmed:
                warnings = _warning_once(
                    candidate.warnings,
                    "TUTOR_MEMORY_SIZE_LIMIT",
                    "Old conversation records were removed to keep the file size bounded.",
                )
                candidate = candidate.model_copy(update={"warnings": warnings})
                while len(_encoded(candidate)) > MAX_BYTES and records:
                    records.pop(0)
                    candidate = candidate.model_copy(update={"records": list(records)})
            self._write(candidate)
            return record

    def _write(self, bundle: TutorMemoryBundle) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path.with_name(f".tutor_memory.{uuid.uuid4().hex}.tmp")
        data = _encoded(bundle)
        try:
            with target.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(5):
                try:
                    os.replace(target, self.path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    # Windows scanners can hold the just-flushed file for a
                    # few milliseconds even though application writers share
                    # the same per-path lock.
                    time.sleep(0.01 * (attempt + 1))
        finally:
            target.unlink(missing_ok=True)


def _encoded(bundle: TutorMemoryBundle) -> bytes:
    return json.dumps(
        bundle.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _dedupe_key(record: TutorMemoryRecord) -> tuple[str, str, str]:
    return (
        record.memory_type.strip().lower(),
        record.question.strip().lower(),
        record.answer.strip().lower(),
    )


def _is_useful(record: TutorMemoryRecord) -> bool:
    content = f"{record.text} {record.question} {record.answer}".strip().lower()
    if not record.question.strip() and not record.answer.strip():
        return False
    internal_markers = ("booktabs", "multirow", "full_text", "canonical_paper.md")
    return not all(marker in content for marker in ("booktabs", "multirow", "full_text")) \
        and not content.startswith(internal_markers)


def _warning_once(
    warnings: list[WarningItem],
    code: str,
    message: str,
) -> list[WarningItem]:
    if any(item.code == code for item in warnings):
        return list(warnings)
    return [*warnings, WarningItem(code=code, message=message)]
