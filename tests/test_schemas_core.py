from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from researchsensei.schemas import (
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    ErrorItem,
    JobRecord,
    JobStatus,
    StatusEnvelope,
    WarningItem,
    WorkspaceArtifact,
)


def test_status_envelope_serializes_and_validates_from_json() -> None:
    envelope = StatusEnvelope(
        status="ok",
        message="ready",
        warnings=[WarningItem(code="W1", message="minor")],
        data={"phase": 2},
    )

    payload = envelope.model_dump_json()
    restored = StatusEnvelope.model_validate_json(payload)

    assert restored.status == "ok"
    assert restored.warnings[0].code == "W1"
    assert restored.data == {"phase": 2}


def test_status_envelope_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        StatusEnvelope(status="ok", message="ready", unexpected=True)


def test_error_item_requires_code_and_message() -> None:
    with pytest.raises(ValidationError):
        ErrorItem(code="ONLY_CODE")


def test_enum_values_are_closed() -> None:
    with pytest.raises(ValidationError):
        DocumentBlock(block_id="b1", type="unknown", text="x", evidence_ref="b1")


def test_document_ingestion_round_trips_json_with_chinese_text() -> None:
    ingestion = DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            DocumentBlock(
                block_id="b1",
                type=BlockType.PARAGRAPH,
                section="摘要",
                text="这是一段中文。",
                evidence_ref="paper-1:b1",
            )
        ],
    )

    data = json.loads(ingestion.model_dump_json())
    restored = DocumentIngestion.model_validate(data)

    assert restored.blocks[0].section == "摘要"
    assert restored.blocks[0].text == "这是一段中文。"


def test_job_record_has_strict_status_and_artifacts() -> None:
    record = JobRecord(
        job_id="job-1",
        status=JobStatus.PENDING,
        source_path="workspace/runs/job-1/source.txt",
        run_dir="workspace/runs/job-1",
        artifacts=[WorkspaceArtifact(artifact_type="ingestion", path="parsed_document.json")],
    )

    restored = JobRecord.model_validate_json(record.model_dump_json())

    assert restored.status == JobStatus.PENDING
    assert restored.artifacts[0].artifact_type == "ingestion"
