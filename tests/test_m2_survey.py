from __future__ import annotations

import json
from pathlib import Path

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.evidence.claim_extractor import build_claim_evidence
from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.m2.survey import build_survey_artifacts
from researchsensei.schemas.audit import ArtifactBundle
from researchsensei.schemas.document import DocumentBlock, DocumentIngestion
from researchsensei.schemas.enums import BlockType


def _survey_document() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="survey_demo",
        source_path="canonical_paper.md",
        parser_name="m1_canonical_bundle",
        blocks=[
            DocumentBlock(
                block_id="b_title",
                type=BlockType.TITLE,
                text="A Survey of Time Series Anomaly Detection",
                evidence_ref="survey_demo:b_title",
                section="Title",
            ),
            DocumentBlock(
                block_id="b_abs",
                type=BlockType.ABSTRACT,
                text=(
                    "This survey reviews time series anomaly detection methods and presents "
                    "a taxonomy of reconstruction methods, forecasting methods, and graph methods."
                ),
                evidence_ref="survey_demo:b_abs",
                section="Abstract",
            ),
            DocumentBlock(
                block_id="b_intro",
                type=BlockType.PARAGRAPH,
                text=(
                    "Representative graph methods include GDN [12], which proposed graph "
                    "structure learning for sensor anomaly detection. We organize approaches "
                    "into reconstruction methods and prediction methods for comparison."
                ),
                evidence_ref="survey_demo:b_intro",
                section="Introduction",
            ),
        ],
    )


def _write_survey_m1_bundle(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "visual_audit").mkdir()
    canonical = "\n".join([
        "---",
        "paper_id: survey_demo",
        'title: "A Survey of Time Series Anomaly Detection"',
        "canonical_quality_status: PASS",
        "canonicalization_status: success",
        "m2_ready: true",
        "m2_ready_for_formula_understanding: true",
        "primary_parser: mineru25pro",
        "formula_slot_count: 0",
        "---",
        "",
        "# A Survey of Time Series Anomaly Detection",
        "",
        "## Abstract",
        "",
        "This survey reviews time series anomaly detection methods and presents a taxonomy of reconstruction methods, forecasting methods, and graph methods.",
        "",
        "## Introduction",
        "",
        "Representative graph methods include GDN [12], which proposed graph structure learning for sensor anomaly detection. We organize approaches into reconstruction methods and prediction methods for comparison.",
    ])
    (root / "canonical_paper.md").write_text(canonical, encoding="utf-8")
    blocks = []
    for order, block in enumerate(_survey_document().blocks):
        blocks.append({
            "block_id": block.block_id,
            "page": 1,
            "bbox": [0.1, 0.1 + order * 0.1, 0.8, 0.18 + order * 0.1],
            "block_type": block.type.value,
            "text": block.text,
            "latex": "",
            "html": "",
            "reading_order": order,
            "source": "mineru25pro",
            "confidence": 0.95,
            "parent_section": "",
            "raw_payload_ref": "page_001.json",
            "section": block.section,
            "section_confidence": "high",
            "section_reason": "fixture",
            "risk_flags": [],
        })
    (root / "document_blocks.json").write_text(json.dumps(blocks, indent=2), encoding="utf-8")
    (root / "formula_slots.json").write_text("[]", encoding="utf-8")
    (root / "formula_slots.md").write_text("# Formula Slots\n", encoding="utf-8")
    (root / "paper_metadata.json").write_text(
        json.dumps({"paper_id": "survey_demo", "title": "A Survey of Time Series Anomaly Detection"}),
        encoding="utf-8",
    )
    (root / "quality_report.md").write_text("# Quality\nMachine quality gate: PASS\n", encoding="utf-8")
    (root / "performance_report.json").write_text(json.dumps({"perf_pass": True, "warnings": []}), encoding="utf-8")
    return root


def test_survey_artifacts_extract_taxonomy_and_key_papers_with_trace() -> None:
    document = _survey_document()
    passage_index = build_passage_index(document)
    claim_evidence = build_claim_evidence(document, passage_index)

    artifacts = build_survey_artifacts(document, passage_index, claim_evidence)

    assert artifacts["survey_status"]["status"] == "PASS"
    assert artifacts["survey_landscape"]["trusted"] is True
    assert artifacts["method_taxonomy"]["taxonomy"]
    assert artifacts["extracted_key_papers"]["papers"]
    for item in artifacts["method_taxonomy"]["taxonomy"] + artifacts["extracted_key_papers"]["papers"]:
        assert item["evidence_ref"]
        assert item["passage_id"]


def test_quality_auditor_blocks_untraceable_survey_evidence() -> None:
    document = _survey_document()
    passage_index = build_passage_index(document)
    claim_evidence = build_claim_evidence(document, passage_index)
    artifacts = build_survey_artifacts(document, passage_index, claim_evidence)
    artifacts["method_taxonomy"]["taxonomy"][0]["evidence_ref"] = "survey_demo:missing"

    report = QualityAuditor().audit(ArtifactBundle(
        passage_index=passage_index.model_dump(mode="json"),
        claim_evidence=claim_evidence.model_dump(mode="json"),
        survey_status=artifacts["survey_status"],
        survey_landscape=artifacts["survey_landscape"],
        method_taxonomy=artifacts["method_taxonomy"],
        extracted_key_papers=artifacts["extracted_key_papers"],
        survey_claims=artifacts["survey_claims"],
    ))

    assert any(f.code == "S-2" and f.effect == "BLOCK" for f in report.findings)


def test_m2_full_pipeline_writes_survey_artifacts(tmp_path: Path) -> None:
    from researchsensei.m2.full_pipeline import run_m2_full_pipeline

    input_dir = _write_survey_m1_bundle(tmp_path / "m1_survey")
    output_dir = tmp_path / "m2_survey"

    result = run_m2_full_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result.status.status == "BASELINE_ONLY"
    for name in [
        "survey_status.json",
        "survey_landscape.json",
        "method_taxonomy.json",
        "extracted_key_papers.json",
        "survey_claims.json",
    ]:
        assert (output_dir / name).exists(), name
    survey_status = json.loads((output_dir / "survey_status.json").read_text(encoding="utf-8"))
    method_taxonomy = json.loads((output_dir / "method_taxonomy.json").read_text(encoding="utf-8"))
    assert survey_status["status"] == "PASS"
    assert method_taxonomy["taxonomy"]
