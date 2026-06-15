from __future__ import annotations

import json

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.schemas import (
    ArtifactBundle,
    AuditFinding,
    ComponentAuditResult,
    QualityReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_success_status() -> dict:
    return {
        "schema_version": "v1",
        "paper_id": "test",
        "status": "SUCCESS",
        "blocking_reason": "",
        "allowed_for_user_display": True,
        "allowed_downstream": {
            "reading_display": True,
            "phase12_patterns": True,
            "phase12_drill": True,
            "phase12_drill_degraded": False,
            "advisor_questions": True,
        },
        "component_status": {
            "paper_card": "SUCCESS",
            "formula_cards": "SUCCESS",
            "teaching_cards": "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
        },
    }


def _make_paper_card() -> dict:
    return {
        "paper_id": "test",
        "title": "Test Paper",
        "one_sentence_summary": "We propose a GNN.",
        "problem": {"text": "Detecting anomalies.", "evidence_ref": "test:b001"},
        "core_idea": {"text": "Graph neural network.", "evidence_ref": "test:b002"},
        "method_overview": {"text": "GNN approach.", "evidence_ref": "test:b002"},
        "experiment_summary": {"text": "95 F1.", "evidence_ref": "test:b003"},
        "limitations": {"text": "Needs more data.", "evidence_ref": ""},
    }


def _make_evidence_index() -> dict:
    return {
        "paper_id": "test",
        "claims": [
            {"claim_id": "c1", "evidence_ref": "test:b001", "claim_text": "P", "quote_or_summary": "Detecting anomalies in graph transformer signals."},
            {"claim_id": "c2", "evidence_ref": "test:b002", "claim_text": "M", "quote_or_summary": "Graph neural network approach for anomaly detection."},
            {"claim_id": "c3", "evidence_ref": "test:b003", "claim_text": "R", "quote_or_summary": "The model reports 95 F1 on benchmark datasets."},
        ],
        "warnings": [],
    }


def _make_claim_evidence() -> dict:
    return {
        "schema_version": "v2",
        "paper_id": "test",
        "claims": [
            {
                "claim_id": "test:claim:c000",
                "evidence_ref": "test:b001",
                "passage_id": "p001",
                "claim_type": "PROBLEM",
                "claim_text": "Detecting anomalies in graph transformer signals.",
                "quote_or_summary": "Detecting anomalies in graph transformer signals.",
                "canonical_source_path": "canonical_paper.md",
                "block_source": "mineru25pro",
            },
            {
                "claim_id": "test:claim:c001",
                "evidence_ref": "test:b002",
                "passage_id": "p002",
                "claim_type": "METHOD",
                "claim_text": "Graph neural network approach for anomaly detection.",
                "quote_or_summary": "Graph neural network approach for anomaly detection.",
                "canonical_source_path": "canonical_paper.md",
                "block_source": "mineru25pro",
            },
            {
                "claim_id": "test:claim:c002",
                "evidence_ref": "test:b003",
                "passage_id": "p003",
                "claim_type": "RESULT",
                "claim_text": "The model reports 95 F1 on benchmark datasets.",
                "quote_or_summary": "The model reports 95 F1 on benchmark datasets.",
                "canonical_source_path": "canonical_paper.md",
                "block_source": "mineru25pro",
            },
        ],
    }


def _make_passage_index() -> dict:
    return {
        "schema_version": "v2",
        "paper_id": "test",
        "passages": [
            {"passage_id": "p001", "text": "Abstract text.", "section": "abstract"},
            {"passage_id": "p002", "text": "Method text.", "section": "method"},
            {"passage_id": "p003", "text": "Results text.", "section": "experiments"},
        ],
    }


def _make_formula_cards() -> dict:
    return {
        "paper_id": "test",
        "formula_cards": [
            {
                "formula_id": "eq1",
                "purpose": "Loss",
                "evidence_ref": "test:b002",
                "formula_origin": "mineru_latex",
                "formula_ocr_status": "not_required",
                "formula_explanation_status": "parser_derived",
                "confidence": 0.6,
            },
        ],
    }


def _make_teaching_cards() -> dict:
    return {
        "paper_id": "test",
        "teaching_cards": [
            {
                "card_id": "t1",
                "human_explanation": "GNN models relationships.",
                "evidence_refs": ["test:b002"],
            },
        ],
    }


def _make_canonical_status() -> dict:
    return {
        "paper_id": "test",
        "canonicalization_status": "success",
        "canonical_quality_status": "PASS",
        "m2_ready": True,
    }


def _make_baseline_status() -> dict:
    return {
        "paper_id": "test",
        "status": "BASELINE_ONLY",
        "blocking_reason": "NO_LLM_CLIENT",
        "allowed_for_user_display": False,
        "allowed_downstream": {
            "reading_display": False,
            "phase12_patterns": False,
            "phase12_drill": False,
            "advisor_questions": False,
        },
        "component_status": {
            "paper_card": "BASELINE",
            "formula_cards": "BASELINE",
            "teaching_cards": "BASELINE",
            "llm": "SKIPPED",
            "evidence_pack": "SKIPPED",
        },
    }


def _make_blocked_status() -> dict:
    return {
        "paper_id": "test",
        "status": "BLOCKED_UNDERSTANDING",
        "blocking_reason": "LLM_FAILED",
        "allowed_for_user_display": False,
        "allowed_downstream": {
            "reading_display": False,
            "phase12_patterns": False,
            "phase12_drill": False,
            "advisor_questions": False,
        },
        "component_status": {
            "paper_card": "FAILED",
            "llm": "FAILED",
            "evidence_pack": "FAILED",
        },
    }


def _make_degraded_status() -> dict:
    return {
        "paper_id": "test",
        "status": "DEGRADED_STRUCTURAL",
        "blocking_reason": "TEACHING_CARDS_FAILED",
        "allowed_for_user_display": True,
        "allowed_downstream": {
            "reading_display": True,
            "phase12_patterns": True,
            "phase12_drill": True,
            "phase12_drill_degraded": True,
            "advisor_questions": False,
        },
        "component_status": {
            "paper_card": "SUCCESS",
            "formula_cards": "SUCCESS",
            "teaching_cards": "FAILED",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
        },
    }


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_audit_finding_round_trip() -> None:
    finding = AuditFinding(
        code="F-1", severity="P0", effect="BLOCK",
        message="Missing evidence_ref", artifact="paper_card", field="problem.evidence_ref",
    )
    json_str = finding.model_dump_json()
    restored = AuditFinding.model_validate_json(json_str)
    assert restored.code == "F-1"
    assert restored.severity == "P0"
    assert restored.effect == "BLOCK"


def test_component_audit_result_round_trip() -> None:
    result = ComponentAuditResult(
        component="evidence_chain", status="PASS",
        findings=[AuditFinding(code="F-6", severity="P0", effect="BLOCK", message="test")],
    )
    json_str = result.model_dump_json()
    restored = ComponentAuditResult.model_validate_json(json_str)
    assert restored.component == "evidence_chain"
    assert len(restored.findings) == 1


def test_quality_report_round_trip() -> None:
    report = QualityReport(
        paper_id="test",
        findings=[],
        component_results=[],
        checked_artifacts=["paper_card"],
    )
    json_str = report.model_dump_json()
    restored = QualityReport.model_validate_json(json_str)
    assert restored.paper_id == "test"
    assert restored.schema_version == "v1"


def test_artifact_bundle_round_trip() -> None:
    bundle = ArtifactBundle(
        paper_card={"paper_id": "test"},
        evidence_index={"paper_id": "test", "claims": []},
    )
    json_str = bundle.model_dump_json()
    restored = ArtifactBundle.model_validate_json(json_str)
    assert restored.paper_card is not None
    assert restored.formula_cards is None


# ---------------------------------------------------------------------------
# Valid artifact tests
# ---------------------------------------------------------------------------


def test_valid_success_artifacts_pass() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        formula_cards=_make_formula_cards(),
        teaching_cards=_make_teaching_cards(),
        canonical_status=_make_canonical_status(),
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        passage_index=_make_passage_index(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    block_findings = [f for f in report.findings if f.effect == "BLOCK"]
    assert len(block_findings) == 0


def test_valid_baseline_only_artifacts_pass() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        formula_cards=_make_formula_cards(),
        teaching_cards=_make_teaching_cards(),
        canonical_status=_make_canonical_status(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_baseline_status(),
    )
    report = auditor.audit(bundle)
    block_findings = [f for f in report.findings if f.effect == "BLOCK"]
    assert len(block_findings) == 0


def test_valid_blocked_without_cards_pass() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        evidence_index=_make_evidence_index(),
        understanding_status=_make_blocked_status(),
    )
    report = auditor.audit(bundle)
    f3_findings = [f for f in report.findings if f.code == "F-3"]
    assert len(f3_findings) == 0


def test_valid_degraded_without_teaching_pass() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        formula_cards=_make_formula_cards(),
        canonical_status=_make_canonical_status(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_degraded_status(),
    )
    report = auditor.audit(bundle)
    block_findings = [f for f in report.findings if f.effect == "BLOCK"]
    assert len(block_findings) == 0


# ---------------------------------------------------------------------------
# Finding tests
# ---------------------------------------------------------------------------


def test_missing_core_paper_card_evidence_ref_produces_f1() -> None:
    card = _make_paper_card()
    card["problem"]["evidence_ref"] = ""  # Remove ref
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    f1 = [f for f in report.findings if f.code == "F-1"]
    assert len(f1) >= 1
    assert "problem" in f1[0].field


def test_missing_core_evidence_ref_without_evidence_sources_still_produces_f1() -> None:
    """F-1 should fire even when no evidence_index or claim_evidence is provided."""
    card = _make_paper_card()
    card["problem"]["evidence_ref"] = ""
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=card,
        understanding_status=_make_success_status(),
        # No evidence_index, no claim_evidence
    )
    report = auditor.audit(bundle)
    f1 = [f for f in report.findings if f.code == "F-1"]
    assert len(f1) >= 1
    assert "problem" in f1[0].field
    # F-2 should not fire since no valid_refs to check against
    f2 = [f for f in report.findings if f.code == "F-2"]
    assert len(f2) == 0


def test_invalid_evidence_ref_produces_f2() -> None:
    card = _make_paper_card()
    card["problem"]["evidence_ref"] = "INVALID:ref"
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    f2 = [f for f in report.findings if f.code == "F-2"]
    assert len(f2) >= 1
    assert "INVALID:ref" in f2[0].message


def test_blocked_status_with_card_artifact_produces_f3() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_blocked_status(),
    )
    report = auditor.audit(bundle)
    f3 = [f for f in report.findings if f.code == "F-3"]
    assert len(f3) >= 1
    assert "paper_card" in f3[0].artifact


def test_baseline_only_display_true_produces_f4() -> None:
    status = _make_baseline_status()
    status["allowed_for_user_display"] = True
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        understanding_status=status,
    )
    report = auditor.audit(bundle)
    f4 = [f for f in report.findings if f.code == "F-4"]
    assert len(f4) == 1


def test_success_component_status_conflict_produces_f5() -> None:
    status = _make_success_status()
    status["component_status"]["paper_card"] = "FAILED"
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        understanding_status=status,
    )
    report = auditor.audit(bundle)
    f5 = [f for f in report.findings if f.code == "F-5"]
    assert len(f5) >= 1
    assert "paper_card" in f5[0].field


def test_claim_evidence_passage_id_missing_produces_f6() -> None:
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"][0]["passage_id"] = "nonexistent"
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        claim_evidence=claim_evidence,
        passage_index=_make_passage_index(),
    )
    report = auditor.audit(bundle)
    f6 = [f for f in report.findings if f.code == "F-6"]
    assert len(f6) == 1
    assert "nonexistent" in f6[0].message


def test_core_claim_raw_copy_produces_f8() -> None:
    card = _make_paper_card()
    copied = (
        "Graph neural network approach for anomaly detection uses graph neural network "
        "approach for anomaly detection with graph neural network approach."
    )
    card["method_overview"] = {"text": copied, "evidence_ref": "test:b002"}
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"][0]["quote_or_summary"] = copied
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        claim_evidence=claim_evidence,
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-8" and f.effect == "BLOCK" for f in report.findings)


def test_generic_paper_output_produces_f9() -> None:
    card = _make_paper_card()
    card["core_idea"] = {
        "text": "This paper proposes a method that improves performance and works well on tasks.",
        "evidence_ref": "test:b002",
    }
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        paper_skeleton={"title": "Graph Transformer Anomaly Detection"},
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-9" and f.effect == "BLOCK" for f in report.findings)


def test_formula_heavy_teaching_explanation_produces_f10() -> None:
    teaching_cards = _make_teaching_cards()
    teaching_cards["teaching_cards"][0]["human_explanation"] = (
        r"L=\sum_{i=1}^{N} x_i^2 + \frac{a_b}{c_d} = \alpha_{\theta}"
    )
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        teaching_cards=teaching_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-10" and f.effect == "BLOCK" for f in report.findings)


def test_limitation_raw_overlap_produces_f11_warning() -> None:
    card = _make_paper_card()
    copied = (
        "Graph neural network approach for anomaly detection uses graph neural network "
        "approach for anomaly detection with graph neural network approach."
    )
    card["limitations"] = {"text": copied, "evidence_ref": "test:b002"}
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"][1]["quote_or_summary"] = copied
    report = QualityAuditor().audit(ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        claim_evidence=claim_evidence,
        understanding_status=_make_success_status(),
    ))
    assert any(f.code == "F-11" and f.effect == "WARNING" for f in report.findings)


def test_teaching_analogy_source_overlap_produces_f12_warning() -> None:
    teaching_cards = _make_teaching_cards()
    copied = "Graph neural network approach for anomaly detection with sensor graph transformer signals."
    teaching_cards["teaching_cards"][0]["analogy_explanation"] = copied
    teaching_cards["teaching_cards"][0]["evidence_refs"] = ["test:b002"]
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"][1]["quote_or_summary"] = copied
    report = QualityAuditor().audit(ArtifactBundle(
        teaching_cards=teaching_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=claim_evidence,
        understanding_status=_make_success_status(),
    ))
    assert any(f.code == "F-12" and f.effect == "WARNING" for f in report.findings)


def test_direction_field_without_evidence_ref_produces_d1() -> None:
    card = _make_paper_card()
    card["method_family"] = {"text": "graph transformer anomaly detection", "evidence_ref": ""}
    report = QualityAuditor().audit(ArtifactBundle(
        paper_card=card,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    ))
    assert any(f.code == "D-1" and f.effect == "BLOCK" for f in report.findings)


def test_canonical_trace_required_produces_f13() -> None:
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"][0]["canonical_source_path"] = "external.txt"
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        claim_evidence=claim_evidence,
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-13" and f.effect == "BLOCK" for f in report.findings)


def test_formula_origin_required_produces_f14() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].pop("formula_origin")
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        formula_cards=formula_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-14" and f.effect == "BLOCK" for f in report.findings)


def test_unknown_formula_origin_with_detailed_derivation_produces_fsa5() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].update({
        "formula_origin": "unknown",
        "formula_ocr_status": "not_available",
        "formula_explanation_status": "degraded",
        "purpose": "This objective optimizes reconstruction and regularization terms.",
        "intuition": "The first term fits the input and the second term constrains the model.",
        "plain_summary": "The formula balances reconstruction fidelity with a penalty.",
        "confidence": 0.3,
    })

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=formula_cards,
        understanding_status=_make_success_status(),
    ))

    assert any(f.code == "FSA-5" and f.effect == "BLOCK" for f in report.findings)


def test_unknown_formula_origin_with_unavailable_explanation_passes_fsa5() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].update({
        "formula_origin": "unknown",
        "formula_ocr_status": "not_available",
        "formula_explanation_status": "degraded",
        "coverage_status": "BLOCKED_RAW_ONLY",
        "derivation_status": "blocked",
        "purpose": "INSUFFICIENT_EVIDENCE: formula provenance is unknown.",
        "symbols": [],
        "terms": [],
        "intuition": "INSUFFICIENT_EVIDENCE",
        "numeric_example": "INSUFFICIENT_EVIDENCE",
        "plain_summary": "INSUFFICIENT_EVIDENCE: detailed formula explanation unavailable.",
        "confidence": 0.0,
    })

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=formula_cards,
        understanding_status=_make_success_status(),
    ))

    assert not any(f.code == "FSA-5" for f in report.findings)


def test_parser_formula_origin_with_evidence_ref_allows_detailed_explanation() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].update({
        "formula_origin": "parser_latex",
        "formula_ocr_status": "not_required",
        "formula_explanation_status": "parser_derived",
        "purpose": "The parser-derived equation defines the model objective.",
        "intuition": "It combines the terms described in the formula evidence.",
        "plain_summary": "This formula summarizes the objective.",
        "confidence": 0.6,
    })

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=formula_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    ))

    assert not any(f.code == "FSA-5" for f in report.findings)
    assert not any(f.effect == "BLOCK" for f in report.findings)


def test_ocr_formula_high_confidence_without_warning_produces_f15() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].update({
        "formula_origin": "ocr_latex",
        "formula_ocr_status": "ocr_success",
        "formula_explanation_status": "original",
        "confidence": 0.95,
        "warnings": [],
    })
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        formula_cards=formula_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-15" and f.effect == "BLOCK" for f in report.findings)


def test_reconstructed_formula_must_be_speculative() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0].update({
        "formula_origin": "reconstructed",
        "formula_ocr_status": "not_required",
        "formula_explanation_status": "parser_derived",
        "confidence": 0.8,
    })
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        formula_cards=formula_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-15" and f.effect == "BLOCK" for f in report.findings)


def test_blocked_canonical_with_user_cards_produces_f16() -> None:
    canonical_status = _make_canonical_status()
    canonical_status["canonicalization_status"] = "blocked"
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        canonical_status=canonical_status,
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert any(f.code == "F-16" and f.effect == "BLOCK" for f in report.findings)


def test_llama_immutable_formula_mutation_produces_fsa12() -> None:
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0]["risk_flags"] = ["LLAMA_MODIFIED_FORMULA_LATEX"]
    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=formula_cards,
        evidence_index=_make_evidence_index(),
        claim_evidence=_make_claim_evidence(),
        understanding_status=_make_success_status(),
    ))
    assert any(f.code == "FSA-12" and f.effect == "BLOCK" for f in report.findings)


def test_formula_card_missing_formula_evidence_ref_produces_fsa13() -> None:
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"].extend([
        {
            "claim_id": "test:claim:f001",
            "evidence_ref": "test:eq001",
            "passage_id": "p004",
            "claim_type": "FORMULA_CONTEXT",
            "claim_text": "Formula one",
            "quote_or_summary": "Formula one",
            "canonical_source_path": "canonical_paper.md",
            "formula_id": "formula_001",
            "formula_origin": "mineru_latex",
        },
        {
            "claim_id": "test:claim:f002",
            "evidence_ref": "test:eq002",
            "passage_id": "p005",
            "claim_type": "FORMULA_CONTEXT",
            "claim_text": "Formula two",
            "quote_or_summary": "Formula two",
            "canonical_source_path": "canonical_paper.md",
            "formula_id": "formula_002",
            "formula_origin": "mineru_latex",
        },
    ])
    formula_cards = _make_formula_cards()
    formula_cards["formula_cards"][0]["evidence_ref"] = "test:eq001"

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=formula_cards,
        canonical_status=_make_canonical_status(),
        claim_evidence=claim_evidence,
        understanding_status=_make_success_status(),
    ))

    assert any(f.code == "FSA-13" and f.effect == "BLOCK" for f in report.findings)


def test_formula_card_coverage_skips_when_m1_formula_understanding_not_ready() -> None:
    claim_evidence = _make_claim_evidence()
    claim_evidence["claims"].append({
        "claim_id": "test:claim:f001",
        "evidence_ref": "test:eq001",
        "passage_id": "p004",
        "claim_type": "FORMULA_CONTEXT",
        "claim_text": "Formula one",
        "quote_or_summary": "Formula one",
        "canonical_source_path": "canonical_paper.md",
        "formula_id": "formula_001",
        "formula_origin": "raw_formula_text",
    })
    canonical_status = _make_canonical_status()
    canonical_status["m2_ready_for_formula_understanding"] = False

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards={"paper_id": "test", "formula_cards": []},
        canonical_status=canonical_status,
        claim_evidence=claim_evidence,
        understanding_status=_make_degraded_status(),
    ))

    assert not any(f.code == "FSA-13" for f in report.findings)


# ---------------------------------------------------------------------------
# Independence tests
# ---------------------------------------------------------------------------


def test_auditor_does_not_import_old_builders() -> None:
    import researchsensei.audit.quality_auditor as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "from researchsensei.paper_card import" not in source
    assert "from researchsensei.formula_card import" not in source
    assert "from researchsensei.teaching_card import" not in source


def test_auditor_does_not_import_v2_builders() -> None:
    import researchsensei.audit.quality_auditor as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "paper_card_v2" not in source
    assert "formula_card_v2" not in source
    assert "teaching_card_v2" not in source


def test_auditor_does_not_write_files(tmp_path) -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_success_status(),
    )
    auditor.audit(bundle)
    json_files = list(tmp_path.rglob("*.json"))
    assert json_files == []


def test_auditor_does_not_require_workspace_store() -> None:
    auditor = QualityAuditor()
    assert not hasattr(auditor, "workspace")
    assert not hasattr(auditor, "jobs")


# ---------------------------------------------------------------------------
# Other tests
# ---------------------------------------------------------------------------


def test_checked_artifacts_records_present_artifacts() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_success_status(),
    )
    report = auditor.audit(bundle)
    assert "paper_card" in report.checked_artifacts
    assert "evidence_index" in report.checked_artifacts
    assert "understanding_status" in report.checked_artifacts
    assert "formula_cards" not in report.checked_artifacts


def test_component_results_status_fail_when_block_finding() -> None:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_make_paper_card(),
        evidence_index=_make_evidence_index(),
        understanding_status=_make_blocked_status(),
    )
    report = auditor.audit(bundle)
    status_gate = [c for c in report.component_results if c.component == "status_gate"]
    assert len(status_gate) == 1
    assert status_gate[0].status == "FAIL"
