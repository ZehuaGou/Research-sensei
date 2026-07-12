from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import researchsensei.m4.service as m4_service
from researchsensei.m4.service import M4InteractionService


def test_m4_memory_concurrent_writes_do_not_lose_records(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"

    def write_record(index: int) -> None:
        service = _service(run_dir)
        _append(service, question=f"question-{index}", answer=f"answer-{index}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_record, range(24)))

    bundle = _service(run_dir).get_memory()
    assert len(bundle.records) == 24
    assert {record.question for record in bundle.records} == {f"question-{index}" for index in range(24)}
    assert json.loads((run_dir / "m4_memory.json").read_text(encoding="utf-8"))["schema_version"] == "m4_memory.v2"


def test_m4_memory_atomic_replace_failure_preserves_previous_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path / "run")
    _append(service, question="stable", answer="stable answer")
    before = service.memory_path.read_bytes()
    real_replace = m4_service.os.replace

    def fail_temp_replace(source: str | Path, target: str | Path) -> None:
        if str(source).endswith(".tmp"):
            raise OSError("simulated replace failure")
        real_replace(source, target)

    monkeypatch.setattr(m4_service.os, "replace", fail_temp_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        _append(service, question="not committed", answer="new answer")

    assert service.memory_path.read_bytes() == before
    assert list(service.run_dir.glob(".*.tmp")) == []


def test_m4_memory_interrupted_write_preserves_previous_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path / "run")
    _append(service, question="stable", answer="stable answer")
    before = service.memory_path.read_bytes()

    def fail_fsync(_fd: int) -> None:
        raise OSError("simulated interrupted write")

    monkeypatch.setattr(m4_service.os, "fsync", fail_fsync)

    with pytest.raises(OSError, match="simulated interrupted write"):
        _append(service, question="not committed", answer="new answer")

    assert service.memory_path.read_bytes() == before
    assert list(service.run_dir.glob(".*.tmp")) == []


def test_m4_memory_corruption_is_preserved_and_reported(tmp_path: Path) -> None:
    service = _service(tmp_path / "run")
    service.run_dir.mkdir(parents=True)
    corrupt_bytes = b'{"schema_version": "m4_memory.v2", broken'
    service.memory_path.write_bytes(corrupt_bytes)

    bundle = service.get_memory()

    assert bundle.records == []
    assert bundle.warnings[0].code == "M4_MEMORY_CORRUPTED"
    assert not service.memory_path.exists()
    preserved = list(service.run_dir.glob("m4_memory.corrupt-*.json"))
    assert len(preserved) == 1
    assert preserved[0].read_bytes() == corrupt_bytes

    _append(service, question="after recovery", answer="grounded answer")
    recovered = service.get_memory()
    assert [record.question for record in recovered.records] == ["after recovery"]
    assert service.memory_path.exists()
    assert preserved[0].read_bytes() == corrupt_bytes


def test_m4_memory_migrates_legacy_schema_on_next_write(tmp_path: Path) -> None:
    service = _service(tmp_path / "run")
    service.run_dir.mkdir(parents=True)
    legacy = {
        "schema_version": "m4_memory",
        "job_id": "job-1",
        "records": [
            {
                "memory_id": "m4_legacy",
                "job_id": "job-1",
                "memory_type": "selection_explanation",
                "text": "legacy evidence",
                "question": "legacy question",
                "answer": "legacy answer",
                "source_artifact": "claim_evidence",
                "evidence_refs": ["paper:b001"],
                "confidence": 0.8,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            }
        ],
    }
    service.memory_path.write_text(json.dumps(legacy), encoding="utf-8")

    migrated = service.get_memory()

    assert migrated.schema_version == "m4_memory.v2"
    assert migrated.migrated_from == "m4_memory"
    assert migrated.warnings[0].code == "M4_MEMORY_SCHEMA_MIGRATED"
    assert [record.memory_id for record in migrated.records] == ["m4_legacy"]

    _append(service, question="new question", answer="new answer")
    persisted = json.loads(service.memory_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "m4_memory.v2"
    assert persisted["migrated_from"] == "m4_memory"
    assert len(persisted["records"]) == 2


def test_m4_memory_enforces_record_and_file_size_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m4_service, "M4_MEMORY_MAX_RECORDS", 5)
    monkeypatch.setattr(m4_service, "M4_MEMORY_MAX_BYTES", 3_200)
    service = _service(tmp_path / "run")

    for index in range(20):
        _append(
            service,
            question=f"question-{index}",
            answer=f"answer-{index}-" + ("evidence " * 30),
        )

    bundle = service.get_memory()
    assert len(bundle.records) <= 5
    assert bundle.records[-1].question == "question-19"
    assert service.memory_path.stat().st_size <= 3_200
    warning_codes = {warning.code for warning in bundle.warnings}
    assert warning_codes & {"M4_MEMORY_RECORD_LIMIT", "M4_MEMORY_SIZE_LIMIT"}


def test_m4_memory_cleans_blank_low_quality_and_duplicate_records(tmp_path: Path) -> None:
    service = _service(tmp_path / "run")
    _append(service, question="", answer="", text="")
    _append(service, question="same", answer="grounded answer")
    _append(service, question="same", answer="grounded answer")
    _append(service, question="bad", answer="booktabs multirow full_text")

    bundle = service.get_memory()

    assert [(record.question, record.answer) for record in bundle.records] == [("same", "grounded answer")]
    assert "M4_MEMORY_RECORDS_CLEANED" in {warning.code for warning in bundle.warnings}


def _service(run_dir: Path) -> M4InteractionService:
    return M4InteractionService(
        job_id="job-1",
        run_dir=run_dir,
        artifacts={},
    )


def _append(
    service: M4InteractionService,
    *,
    question: str,
    answer: str,
    text: str = "evidence",
) -> None:
    service._append_memory(
        memory_type="selection_explanation",
        text=text,
        question=question,
        answer=answer,
        evidence_refs=["paper:b001"],
        confidence=0.8,
        source_artifact="claim_evidence",
    )
