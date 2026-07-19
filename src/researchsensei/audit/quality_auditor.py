from __future__ import annotations

from datetime import datetime, timezone
import re

from researchsensei.schemas.audit import (
    ArtifactBundle,
    AuditFinding,
    ComponentAuditResult,
    QualityReport,
)

# Fields in PaperCard that require evidence_ref
CORE_PAPER_CARD_FIELDS = [
    "problem",
    "core_idea",
    "method_overview",
    "experiment_summary",
]
LIMITATION_COPY_FIELDS = [
    "limitations",
    "bottleneck",
]
DIRECTION_RELATED_FIELDS = [
    "method_family",
    "contribution_to_direction",
    "what_problem_it_solves",
    "what_limitation_it_leaves",
    "relation_to_previous_methods",
    "relation_to_later_methods",
    "datasets_and_metrics",
    "comparable_methods",
]

_GENERIC_OUTPUT_TERMS = {
    "paper", "method", "approach", "model", "proposes", "propose", "improves",
    "improve", "performance", "task", "tasks", "results", "works", "well",
    "better", "novel", "effective", "efficient", "framework", "problem",
    "data", "experiments", "study", "research",
}

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "into", "using", "used", "use", "its", "their", "than", "then", "when",
    "where", "which", "while", "such", "also", "can", "has", "have", "had",
    "not", "but", "between", "among", "based", "paper", "method", "model",
}

_FORMULA_ORIGINS = {
    "source_latex",
    "parser_latex",
    "mineru_latex",
    "marker_latex",
    "ocr_latex",
    "reconstructed",
    "unknown",
    "raw_formula_text",
}

_INSUFFICIENT_CLAIM_TEXTS = {
    "",
    "UNKNOWN",
    "INSUFFICIENT_EVIDENCE",
    "NEEDS_HUMAN_CHECK",
    "证据不足，暂不展开。",
}

# Expected component_status values for each understanding status
_STATUS_EXPECTED_COMPONENTS: dict[str, dict[str, str]] = {
    "SUCCESS": {
        "paper_card": "SUCCESS",
        "teaching_cards": "SUCCESS",
        "llm": "SUCCESS",
        "evidence_pack": "SUCCESS",
    },
    "BASELINE_ONLY": {
        "paper_card": "BASELINE",
        "formula_cards": "BASELINE",
        "teaching_cards": "BASELINE",
        "llm": "SKIPPED",
    },
    "BLOCKED_UNDERSTANDING": {},
    "DEGRADED_STRUCTURAL": {},
}


def _is_explicitly_insufficient_claim(claim: dict) -> bool:
    evidence_type = str(claim.get("evidence_type") or "").strip().upper()
    text = str(claim.get("text") or "").strip()
    if evidence_type == "INSUFFICIENT_EVIDENCE":
        return True
    return text in _INSUFFICIENT_CLAIM_TEXTS


class QualityAuditor:
    """Rule-based quality auditor.

    Reads ArtifactBundle (serialized dicts), produces QualityReport.
    Does not import card builders, does not write artifacts, does not call LLM.
    """

    def audit(self, artifacts: ArtifactBundle) -> QualityReport:
        paper_id = self._extract_paper_id(artifacts)
        findings: list[AuditFinding] = []
        component_results: list[ComponentAuditResult] = []
        checked_artifacts: list[str] = []

        # Determine which artifacts are present
        if artifacts.canonical_status is not None:
            checked_artifacts.append("canonical_status")
        if artifacts.paper_card is not None:
            checked_artifacts.append("paper_card")
        if artifacts.formula_cards is not None:
            checked_artifacts.append("formula_cards")
        if artifacts.teaching_cards is not None:
            checked_artifacts.append("teaching_cards")
        if artifacts.evidence_index is not None:
            checked_artifacts.append("evidence_index")
        if artifacts.claim_evidence is not None:
            checked_artifacts.append("claim_evidence")
        if artifacts.passage_index is not None:
            checked_artifacts.append("passage_index")
        if artifacts.understanding_status is not None:
            checked_artifacts.append("understanding_status")
        if artifacts.survey_status is not None:
            checked_artifacts.append("survey_status")
        if artifacts.survey_landscape is not None:
            checked_artifacts.append("survey_landscape")
        if artifacts.method_taxonomy is not None:
            checked_artifacts.append("method_taxonomy")
        if artifacts.extracted_key_papers is not None:
            checked_artifacts.append("extracted_key_papers")
        if artifacts.survey_claims is not None:
            checked_artifacts.append("survey_claims")

        # Run checks
        evidence_findings = self._check_evidence_chain(artifacts)
        status_findings = self._check_status_gate(artifacts)
        card_ref_findings = self._check_card_refs(artifacts)
        content_findings = self._check_content_quality(artifacts)
        formula_findings = self._check_formula_source(artifacts)
        survey_findings = self._check_survey_trace(artifacts)

        findings.extend(evidence_findings)
        findings.extend(status_findings)
        findings.extend(card_ref_findings)
        findings.extend(content_findings)
        findings.extend(formula_findings)
        findings.extend(survey_findings)

        # Build component results
        component_results.append(ComponentAuditResult(
            component="evidence_chain",
            status="FAIL" if any(f.effect == "BLOCK" for f in evidence_findings) else "PASS",
            findings=evidence_findings,
        ))
        component_results.append(ComponentAuditResult(
            component="status_gate",
            status="FAIL" if any(f.effect == "BLOCK" for f in status_findings) else "PASS",
            findings=status_findings,
        ))
        component_results.append(ComponentAuditResult(
            component="card_refs",
            status="FAIL" if any(f.effect == "BLOCK" for f in card_ref_findings) else "PASS",
            findings=card_ref_findings,
        ))
        component_results.append(ComponentAuditResult(
            component="content_quality",
            status="FAIL" if any(f.effect == "BLOCK" for f in content_findings) else "PASS",
            findings=content_findings,
        ))
        component_results.append(ComponentAuditResult(
            component="formula_source",
            status="FAIL" if any(f.effect == "BLOCK" for f in formula_findings) else "PASS",
            findings=formula_findings,
        ))
        component_results.append(ComponentAuditResult(
            component="survey_trace",
            status="FAIL" if any(f.effect == "BLOCK" for f in survey_findings) else "PASS",
            findings=survey_findings,
        ))

        return QualityReport(
            paper_id=paper_id,
            findings=findings,
            component_results=component_results,
            checked_artifacts=checked_artifacts,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Evidence chain checks
    # ------------------------------------------------------------------

    def _check_evidence_chain(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        # F-6: ClaimEvidenceRecord.passage_id not in PassageIndex
        if artifacts.claim_evidence and artifacts.passage_index:
            passage_ids = {
                p.get("passage_id", "")
                for p in artifacts.passage_index.get("passages", [])
            }
            for claim in artifacts.claim_evidence.get("claims", []):
                pid = claim.get("passage_id", "")
                if pid and pid not in passage_ids:
                    findings.append(AuditFinding(
                        code="F-6",
                        severity="P0",
                        effect="BLOCK",
                        message=f"ClaimEvidence passage_id '{pid}' not found in PassageIndex",
                        artifact="claim_evidence",
                        field=f"claim[{claim.get('claim_id', '')}].passage_id",
                    ))

        return findings

    # ------------------------------------------------------------------
    # Content quality checks
    # ------------------------------------------------------------------

    def _check_content_quality(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if artifacts.paper_card:
            findings.extend(self._check_raw_copy_and_generic_paper_fields(artifacts))
            findings.extend(self._check_limitation_quote_overlap(artifacts))
            findings.extend(self._check_direction_fields_have_refs(artifacts))
        if artifacts.teaching_cards:
            findings.extend(self._check_teaching_formula_heavy(artifacts))
            findings.extend(self._check_teaching_analogy_overlap(artifacts))
        return findings

    def _check_raw_copy_and_generic_paper_fields(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        paper_card = artifacts.paper_card or {}
        evidence_by_ref = self._evidence_text_by_ref(artifacts)
        paper_terms = self._paper_specific_terms(artifacts)

        for field_name in CORE_PAPER_CARD_FIELDS:
            field_val = paper_card.get(field_name)
            if not isinstance(field_val, dict):
                continue
            text = str(field_val.get("text") or "")
            ref = str(field_val.get("evidence_ref") or "")
            if not text or text == "UNKNOWN" or text == "INSUFFICIENT_EVIDENCE":
                continue

            evidence_text = evidence_by_ref.get(ref, "")
            if evidence_text and self._token_overlap(text, evidence_text) > 0.8 and len(self._tokens(text)) >= 12:
                findings.append(AuditFinding(
                    code="F-8",
                    severity="P0",
                    effect="BLOCK",
                    message=f"paper_card.{field_name} appears to be a raw copy of its evidence passage",
                    artifact="paper_card",
                    field=f"{field_name}.text",
                ))

            if self._looks_generic(text, paper_terms):
                findings.append(AuditFinding(
                    code="F-9",
                    severity="P1",
                    effect="BLOCK",
                    message=f"paper_card.{field_name} is too generic and lacks paper-specific terms",
                    artifact="paper_card",
                    field=f"{field_name}.text",
                ))

        return findings

    def _check_limitation_quote_overlap(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        paper_card = artifacts.paper_card or {}
        evidence_by_ref = self._evidence_text_by_ref(artifacts)
        for field_name in LIMITATION_COPY_FIELDS:
            field_val = paper_card.get(field_name)
            if not isinstance(field_val, dict):
                continue
            text = str(field_val.get("text") or "")
            ref = str(field_val.get("evidence_ref") or "")
            evidence_text = evidence_by_ref.get(ref, "")
            if evidence_text and self._token_overlap(text, evidence_text) > 0.7 and len(self._tokens(text)) >= 12:
                findings.append(AuditFinding(
                    code="F-11",
                    severity="P2",
                    effect="WARNING",
                    message=f"paper_card.{field_name} closely overlaps its evidence passage; consider summarizing rather than quoting",
                    artifact="paper_card",
                    field=f"{field_name}.text",
                ))
        return findings

    def _check_direction_fields_have_refs(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        paper_card = artifacts.paper_card or {}
        for field_name in DIRECTION_RELATED_FIELDS:
            if field_name not in paper_card:
                continue
            value = paper_card.get(field_name)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, dict):
                text = str(value.get("text") or value.get("value") or "")
                ref = str(value.get("evidence_ref") or "")
            else:
                text = str(value)
                ref = ""
            if text and text != "INSUFFICIENT_EVIDENCE" and not ref:
                findings.append(AuditFinding(
                    code="D-1",
                    severity="P0",
                    effect="BLOCK",
                    message=f"paper_card.{field_name} is direction-related but has no evidence_ref",
                    artifact="paper_card",
                    field=field_name,
                ))
        return findings

    def _check_teaching_formula_heavy(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        for i, card in enumerate((artifacts.teaching_cards or {}).get("teaching_cards", [])):
            text = str(card.get("human_explanation") or "")
            if not text:
                continue
            ratio = self._formula_char_ratio(text)
            if ratio >= 0.3:
                findings.append(AuditFinding(
                    code="F-10",
                    severity="P0",
                    effect="BLOCK",
                    message=f"teaching_cards[{i}].human_explanation is formula-heavy (ratio={ratio:.2f})",
                    artifact="teaching_cards",
                    field=f"teaching_cards[{i}].human_explanation",
                ))
        return findings

    def _check_teaching_analogy_overlap(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        evidence_by_ref = self._evidence_text_by_ref(artifacts)
        for i, card in enumerate((artifacts.teaching_cards or {}).get("teaching_cards", [])):
            text = str(card.get("analogy_explanation") or "")
            if not text:
                continue
            refs = [str(card.get("evidence_ref") or "")]
            refs.extend(str(ref) for ref in card.get("evidence_refs", []))
            for ref in refs:
                evidence_text = evidence_by_ref.get(ref, "")
                if evidence_text and self._token_overlap(text, evidence_text) > 0.5 and len(self._tokens(text)) >= 8:
                    findings.append(AuditFinding(
                        code="F-12",
                        severity="P2",
                        effect="WARNING",
                        message=f"teaching_cards[{i}].analogy_explanation overlaps source text; analogy may be copied rather than explanatory",
                        artifact="teaching_cards",
                        field=f"teaching_cards[{i}].analogy_explanation",
                    ))
                    break
        return findings


    # ------------------------------------------------------------------
    # Formula source / canonical provenance checks
    # ------------------------------------------------------------------

    def _check_formula_source(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        findings.extend(self._check_canonical_trace(artifacts))
        findings.extend(self._check_formula_cards_provenance(artifacts))
        findings.extend(self._check_formula_card_coverage(artifacts))
        findings.extend(self._check_blocked_canonical_no_cards(artifacts))
        findings.extend(self._check_formula_claim_risks(artifacts))
        return findings

    def _check_canonical_trace(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        claims_by_ref = {
            str(claim.get("evidence_ref") or ""): claim
            for claim in (artifacts.claim_evidence or {}).get("claims", [])
            if str(claim.get("evidence_ref") or "")
        }
        if not claims_by_ref:
            return findings

        for artifact, field, ref in self._iter_card_refs(artifacts):
            claim = claims_by_ref.get(ref)
            if not claim:
                continue
            source_path = str(claim.get("canonical_source_path") or "")
            if source_path and source_path != "canonical_paper.md":
                findings.append(AuditFinding(
                    code="F-13",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{artifact}.{field} evidence_ref '{ref}' does not trace to canonical_paper.md",
                    artifact=artifact,
                    field=field,
                ))
        return findings

    def _check_formula_cards_provenance(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        us_status = (artifacts.understanding_status or {}).get("status", "")
        if us_status not in {"SUCCESS", "DEGRADED_STRUCTURAL"}:
            return findings

        for i, card in enumerate((artifacts.formula_cards or {}).get("formula_cards", [])):
            origin = str(card.get("formula_origin") or "").strip()
            ocr_status = str(card.get("formula_ocr_status") or "").strip()
            explanation_status = str(card.get("formula_explanation_status") or "").strip().lower()
            warnings = [str(item).lower() for item in card.get("warnings", [])]
            confidence = self._float(card.get("confidence"), 0.0)
            field_prefix = f"formula_cards[{i}]"
            card_risks = [str(item).upper() for item in card.get("risk_flags", [])]

            if not origin or origin not in _FORMULA_ORIGINS:
                findings.append(AuditFinding(
                    code="F-14",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{field_prefix} is missing a valid formula_origin",
                    artifact="formula_cards",
                    field=f"{field_prefix}.formula_origin",
                ))
            if not ocr_status:
                findings.append(AuditFinding(
                    code="F-14",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{field_prefix} is missing formula_ocr_status",
                    artifact="formula_cards",
                    field=f"{field_prefix}.formula_ocr_status",
                ))

            if origin == "source_latex" and not str(card.get("original_latex") or card.get("formula_raw") or "").strip():
                findings.append(AuditFinding(
                    code="FSA-6",
                    severity="P1",
                    effect="BLOCK",
                    message=f"{field_prefix} has source_latex origin but no original_latex/formula_raw",
                    artifact="formula_cards",
                    field=f"{field_prefix}.original_latex",
                ))

            if origin in {"parser_latex", "mineru_latex", "marker_latex"} and "parser" not in explanation_status:
                findings.append(AuditFinding(
                    code="FSA-2",
                    severity="P1",
                    effect="WARNING",
                    message=f"{field_prefix} uses parser-derived LaTeX but formula_explanation_status does not mark parser provenance",
                    artifact="formula_cards",
                    field=f"{field_prefix}.formula_explanation_status",
                ))

            if origin == "ocr_latex":
                has_ocr_warning = any("ocr" in item for item in warnings) or "ocr" in ocr_status.lower()
                if confidence > 0.7 or "original" in explanation_status or not has_ocr_warning:
                    findings.append(AuditFinding(
                        code="F-15",
                        severity="P0",
                        effect="BLOCK",
                        message=f"{field_prefix} uses ocr_latex but is not clearly capped/warned as OCR-derived",
                        artifact="formula_cards",
                        field=f"{field_prefix}.formula_origin",
                    ))

            if origin == "reconstructed":
                if confidence > 0.5 or "speculative" not in explanation_status:
                    findings.append(AuditFinding(
                        code="F-15",
                        severity="P0",
                        effect="BLOCK",
                        message=f"{field_prefix} uses reconstructed formula without speculative low-confidence status",
                        artifact="formula_cards",
                        field=f"{field_prefix}.formula_explanation_status",
                    ))

            if origin == "unknown":
                detail = " ".join(str(card.get(key) or "") for key in ("purpose", "intuition", "plain_summary"))
                if confidence > 0 or "insufficient_evidence" not in detail.lower():
                    findings.append(AuditFinding(
                        code="FSA-5",
                        severity="P0",
                        effect="BLOCK",
                        message=f"{field_prefix} has unknown formula_origin but contains detailed formula explanation",
                        artifact="formula_cards",
                        field=f"{field_prefix}.formula_origin",
                    ))

            if confidence >= 0.85 and origin != "source_latex":
                findings.append(AuditFinding(
                    code="FSA-1",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{field_prefix} is high-confidence but formula_origin is not source_latex",
                    artifact="formula_cards",
                    field=f"{field_prefix}.confidence",
                ))

            if (
                card.get("llama_modified_immutable_fields") is True
                or card.get("immutable_fields_modified") is True
                or any("LLAMA_MODIFIED" in flag or "FORMULA_MUTATION" in flag or "IMMUTABLE_FIELD_MODIFIED" in flag for flag in card_risks)
            ):
                findings.append(AuditFinding(
                    code="FSA-12",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{field_prefix} records Llama/Ollama modification of immutable formula identity",
                    artifact="formula_cards",
                    field=f"{field_prefix}.risk_flags",
                ))

        return findings

    def _check_formula_card_coverage(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        us_status = (artifacts.understanding_status or {}).get("status", "")
        if us_status not in {"SUCCESS", "DEGRADED_STRUCTURAL"}:
            return findings
        canonical_status = artifacts.canonical_status or {}
        if canonical_status.get("m2_ready_for_formula_understanding") is False:
            return findings
        formula_claims = [
            claim for claim in (artifacts.claim_evidence or {}).get("claims", [])
            if str(claim.get("claim_type") or "") == "FORMULA_CONTEXT"
            and str(claim.get("evidence_ref") or "")
        ]
        if not formula_claims:
            return findings
        cards = (artifacts.formula_cards or {}).get("formula_cards", [])
        card_refs = {
            str(card.get("evidence_ref") or "")
            for card in cards
            if isinstance(card, dict) and str(card.get("evidence_ref") or "")
        }
        missing = [
            str(claim.get("evidence_ref") or "")
            for claim in formula_claims
            if str(claim.get("evidence_ref") or "") not in card_refs
        ]
        if missing:
            sample = ", ".join(missing[:5])
            findings.append(AuditFinding(
                code="FSA-13",
                severity="P0",
                effect="BLOCK",
                message=f"formula_cards do not cover all M1 formula evidence refs; missing {len(missing)} refs: {sample}",
                artifact="formula_cards",
                field="formula_cards[].evidence_ref",
            ))
        return findings

    def _check_blocked_canonical_no_cards(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        canonical_status = artifacts.canonical_status or {}
        status = str(canonical_status.get("canonicalization_status") or "").lower()
        quality = str(canonical_status.get("canonical_quality_status") or "").upper()
        display = bool((artifacts.understanding_status or {}).get("allowed_for_user_display", False))
        if status == "blocked" or quality == "FAIL":
            if display or artifacts.paper_card or artifacts.formula_cards or artifacts.teaching_cards:
                findings.append(AuditFinding(
                    code="F-16",
                    severity="P0",
                    effect="BLOCK",
                    message="Blocked/failed canonical input has user-facing card artifacts",
                    artifact="canonical_status",
                    field="canonicalization_status",
                ))
        return findings

    def _check_formula_claim_risks(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        formula_claims = [
            claim for claim in (artifacts.claim_evidence or {}).get("claims", [])
            if str(claim.get("claim_type") or "") == "FORMULA_CONTEXT"
        ]
        abstract_formula_count = sum(
            1 for claim in formula_claims
            if str(claim.get("section") or "").lower() == "abstract"
        )
        if len(formula_claims) >= 5 and abstract_formula_count == len(formula_claims):
            findings.append(AuditFinding(
                code="FSA-9",
                severity="P0",
                effect="BLOCK",
                message="All formula evidence is assigned to Abstract for a formula-heavy paper",
                artifact="claim_evidence",
                field="claims[].section",
            ))

        for claim in formula_claims:
            flags = [str(item).upper() for item in claim.get("risk_flags", [])]
            if any("SECTION_CONTRADICTION" in flag for flag in flags):
                findings.append(AuditFinding(
                    code="FSA-8",
                    severity="P1",
                    effect="WARNING",
                    message=f"Formula claim {claim.get('claim_id', '')} carries section contradiction risk",
                    artifact="claim_evidence",
                    field=f"claim[{claim.get('claim_id', '')}].risk_flags",
                ))
            if claim.get("fallback_used") is True:
                findings.append(AuditFinding(
                    code="FSA-10",
                    severity="P1",
                    effect="WARNING",
                    message=f"Formula claim {claim.get('claim_id', '')} came from a fallback path",
                    artifact="claim_evidence",
                    field=f"claim[{claim.get('claim_id', '')}].fallback_used",
                ))
            if claim.get("llama_refined") is True:
                serialized = str(claim)
                if "api_key" in serialized.lower() or "token" in serialized.lower():
                    findings.append(AuditFinding(
                        code="FSA-11",
                        severity="P1",
                        effect="BLOCK",
                        message=f"Formula claim {claim.get('claim_id', '')} appears to contain secret-like Llama metadata",
                        artifact="claim_evidence",
                        field=f"claim[{claim.get('claim_id', '')}].llama_refined",
                    ))
                else:
                    findings.append(AuditFinding(
                        code="FSA-11",
                        severity="P1",
                        effect="WARNING",
                        message=f"Formula claim {claim.get('claim_id', '')} was Llama-refined; review provenance metadata",
                        artifact="claim_evidence",
                        field=f"claim[{claim.get('claim_id', '')}].llama_refined",
                    ))
            if str(claim.get("formula_ocr_status") or "") == "ocr_failed" and not claim.get("warnings"):
                findings.append(AuditFinding(
                    code="FSA-7",
                    severity="P1",
                    effect="WARNING",
                    message=f"Formula claim {claim.get('claim_id', '')} records OCR failure without warning text",
                    artifact="claim_evidence",
                    field=f"claim[{claim.get('claim_id', '')}].formula_ocr_status",
                ))
            if any("LLAMA_MODIFIED" in flag or "FORMULA_MUTATION" in flag or "IMMUTABLE_FIELD_MODIFIED" in flag for flag in flags):
                findings.append(AuditFinding(
                    code="FSA-12",
                    severity="P0",
                    effect="BLOCK",
                    message=f"Formula claim {claim.get('claim_id', '')} records Llama/Ollama modification of immutable formula identity",
                    artifact="claim_evidence",
                    field=f"claim[{claim.get('claim_id', '')}].risk_flags",
                ))
        return findings

    # ------------------------------------------------------------------
    # Survey trace checks
    # ------------------------------------------------------------------

    def _check_survey_trace(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        if not any([
            artifacts.survey_status,
            artifacts.survey_landscape,
            artifacts.method_taxonomy,
            artifacts.extracted_key_papers,
            artifacts.survey_claims,
        ]):
            return []

        findings: list[AuditFinding] = []
        survey_status = artifacts.survey_status or {}
        if survey_status.get("status") == "NOT_APPLICABLE":
            return findings

        valid_refs, valid_passages = self._survey_valid_sources(artifacts)
        taxonomy = (artifacts.method_taxonomy or {}).get("taxonomy", [])
        key_papers = (artifacts.extracted_key_papers or {}).get("papers", [])
        survey_claims = (artifacts.survey_claims or {}).get("claims", [])
        landscape = artifacts.survey_landscape or {}

        if survey_status.get("is_survey") and landscape.get("trusted") and not taxonomy:
            findings.append(AuditFinding(
                code="S-1",
                severity="P0",
                effect="BLOCK",
                message="Trusted survey_landscape exists without method_taxonomy evidence",
                artifact="survey_landscape",
                field="trusted",
            ))
        if survey_status.get("is_survey") and survey_status.get("status") == "PASS" and not taxonomy:
            findings.append(AuditFinding(
                code="S-1",
                severity="P0",
                effect="BLOCK",
                message="Survey status PASS requires method_taxonomy evidence",
                artifact="survey_status",
                field="status",
            ))

        for artifact, items in (
            ("method_taxonomy", taxonomy),
            ("extracted_key_papers", key_papers),
            ("survey_claims", survey_claims),
        ):
            for index, item in enumerate(items):
                findings.extend(self._check_survey_item_source(
                    artifact=artifact,
                    index=index,
                    item=item,
                    valid_refs=valid_refs,
                    valid_passages=valid_passages,
                ))

        for index, evidence_ref in enumerate(landscape.get("evidence_refs", [])):
            if evidence_ref and evidence_ref not in valid_refs:
                findings.append(AuditFinding(
                    code="S-2",
                    severity="P0",
                    effect="BLOCK",
                    message=f"survey_landscape.evidence_refs[{index}] is not traceable to passage_index",
                    artifact="survey_landscape",
                    field=f"evidence_refs[{index}]",
                ))
        return findings

    def _check_survey_item_source(
        self,
        *,
        artifact: str,
        index: int,
        item: dict,
        valid_refs: set[str],
        valid_passages: set[str],
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        evidence_ref = str(item.get("evidence_ref") or "")
        passage_id = str(item.get("passage_id") or "")
        if not evidence_ref or evidence_ref not in valid_refs:
            findings.append(AuditFinding(
                code="S-2",
                severity="P0",
                effect="BLOCK",
                message=f"{artifact}[{index}] evidence_ref is missing or not traceable to passage_index",
                artifact=artifact,
                field=f"[{index}].evidence_ref",
            ))
        if not passage_id or passage_id not in valid_passages:
            findings.append(AuditFinding(
                code="S-3",
                severity="P0",
                effect="BLOCK",
                message=f"{artifact}[{index}] passage_id is missing or not present in passage_index",
                artifact=artifact,
                field=f"[{index}].passage_id",
            ))
        return findings

    # ------------------------------------------------------------------
    # Status gate checks
    # ------------------------------------------------------------------

    def _check_status_gate(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        us = artifacts.understanding_status
        if us is None:
            return findings

        status = us.get("status", "")
        display = us.get("allowed_for_user_display", False)
        downstream = us.get("allowed_downstream", {})
        comp = us.get("component_status", {})

        # F-4: BASELINE_ONLY allowed_for_user_display=True
        if status == "BASELINE_ONLY" and display is True:
            findings.append(AuditFinding(
                code="F-4",
                severity="P0",
                effect="BLOCK",
                message="BASELINE_ONLY status has allowed_for_user_display=True",
                artifact="understanding_status",
                field="allowed_for_user_display",
            ))

        # F-3: BLOCKED_UNDERSTANDING with card artifacts
        if status == "BLOCKED_UNDERSTANDING":
            if artifacts.paper_card is not None:
                findings.append(AuditFinding(
                    code="F-3",
                    severity="P0",
                    effect="BLOCK",
                    message="BLOCKED_UNDERSTANDING status but paper_card artifact exists",
                    artifact="paper_card",
                ))
            if artifacts.formula_cards is not None:
                findings.append(AuditFinding(
                    code="F-3",
                    severity="P0",
                    effect="BLOCK",
                    message="BLOCKED_UNDERSTANDING status but formula_cards artifact exists",
                    artifact="formula_cards",
                ))
            if artifacts.teaching_cards is not None:
                findings.append(AuditFinding(
                    code="F-3",
                    severity="P0",
                    effect="BLOCK",
                    message="BLOCKED_UNDERSTANDING status but teaching_cards artifact exists",
                    artifact="teaching_cards",
                ))

        # F-5: component_status conflicts
        if status == "SUCCESS":
            for key, expected in _STATUS_EXPECTED_COMPONENTS["SUCCESS"].items():
                actual = comp.get(key, "")
                if actual and actual != expected:
                    findings.append(AuditFinding(
                        code="F-5",
                        severity="P1",
                        effect="BLOCK",
                        message=f"SUCCESS status but component_status['{key}']='{actual}', expected '{expected}'",
                        artifact="understanding_status",
                        field=f"component_status.{key}",
                    ))

        if status == "BASELINE_ONLY":
            for key, expected in _STATUS_EXPECTED_COMPONENTS["BASELINE_ONLY"].items():
                actual = comp.get(key, "")
                if actual and actual != expected:
                    findings.append(AuditFinding(
                        code="F-5",
                        severity="P1",
                        effect="BLOCK",
                        message=f"BASELINE_ONLY status but component_status['{key}']='{actual}', expected '{expected}'",
                        artifact="understanding_status",
                        field=f"component_status.{key}",
                    ))

        if status == "BLOCKED_UNDERSTANDING":
            if display is not False:
                findings.append(AuditFinding(
                    code="F-5",
                    severity="P1",
                    effect="BLOCK",
                    message="BLOCKED_UNDERSTANDING but allowed_for_user_display is not False",
                    artifact="understanding_status",
                    field="allowed_for_user_display",
                ))
            for key, val in downstream.items():
                if val is not False:
                    findings.append(AuditFinding(
                        code="F-5",
                        severity="P1",
                        effect="BLOCK",
                        message=f"BLOCKED_UNDERSTANDING but allowed_downstream.{key} is not False",
                        artifact="understanding_status",
                        field=f"allowed_downstream.{key}",
                    ))

        if status == "DEGRADED_STRUCTURAL":
            if display is not True:
                findings.append(AuditFinding(
                    code="F-5",
                    severity="P1",
                    effect="BLOCK",
                    message="DEGRADED_STRUCTURAL but allowed_for_user_display is not True",
                    artifact="understanding_status",
                    field="allowed_for_user_display",
                ))
            if downstream.get("advisor_questions") is True and comp.get("paper_card") != "SUCCESS":
                findings.append(AuditFinding(
                    code="F-5",
                    severity="P1",
                    effect="BLOCK",
                    message="DEGRADED_STRUCTURAL allows advisor_questions without successful paper_card",
                    artifact="understanding_status",
                    field="allowed_downstream.advisor_questions",
                ))
            if downstream.get("learning_drills") is True and comp.get("teaching_cards") != "SUCCESS":
                findings.append(AuditFinding(
                    code="F-5",
                    severity="P1",
                    effect="BLOCK",
                    message="DEGRADED_STRUCTURAL allows learning_drills without successful teaching_cards",
                    artifact="understanding_status",
                    field="allowed_downstream.learning_drills",
                ))

        return findings

    # ------------------------------------------------------------------
    # Card ref checks
    # ------------------------------------------------------------------

    def _check_card_refs(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        # F-1: core paper_card fields missing evidence_ref (always checked)
        if artifacts.paper_card:
            us_status = ""
            if artifacts.understanding_status:
                us_status = artifacts.understanding_status.get("status", "")

            if us_status in ("SUCCESS", "DEGRADED_STRUCTURAL"):
                for field_name in CORE_PAPER_CARD_FIELDS:
                    field_val = artifacts.paper_card.get(field_name)
                    if field_val is None:
                        continue
                    ref = field_val.get("evidence_ref", "") if isinstance(field_val, dict) else ""
                    if not ref:
                        if isinstance(field_val, dict) and _is_explicitly_insufficient_claim(field_val):
                            findings.append(AuditFinding(
                                code="F-1-DEGRADED",
                                severity="P2",
                                effect="WARNING",
                                message=f"paper_card.{field_name} is explicitly marked as insufficient evidence",
                                artifact="paper_card",
                                field=f"{field_name}.evidence_ref",
                            ))
                            continue
                        findings.append(AuditFinding(
                            code="F-1",
                            severity="P0",
                            effect="BLOCK",
                            message=f"paper_card.{field_name} has no evidence_ref",
                            artifact="paper_card",
                            field=f"{field_name}.evidence_ref",
                        ))

        # Collect all valid evidence_refs for F-2
        valid_refs: set[str] = set()
        if artifacts.evidence_index:
            for claim in artifacts.evidence_index.get("claims", []):
                ref = claim.get("evidence_ref", "")
                if ref:
                    valid_refs.add(ref)
        if artifacts.claim_evidence:
            for claim in artifacts.claim_evidence.get("claims", []):
                ref = claim.get("evidence_ref", "")
                if ref:
                    valid_refs.add(ref)

        if not valid_refs:
            # No evidence sources available — skip F-2 but F-1 already checked
            return findings

        # F-2: evidence_ref not in valid set
        if artifacts.paper_card:
            findings.extend(self._check_refs_in_card(
                artifacts.paper_card, valid_refs, "paper_card",
            ))
        if artifacts.formula_cards:
            for i, fc in enumerate(artifacts.formula_cards.get("formula_cards", [])):
                ref = fc.get("evidence_ref", "")
                if ref and ref not in valid_refs:
                    findings.append(AuditFinding(
                        code="F-2",
                        severity="P0",
                        effect="BLOCK",
                        message=f"formula_cards[{i}].evidence_ref '{ref}' not found in evidence sources",
                        artifact="formula_cards",
                        field=f"formula_cards[{i}].evidence_ref",
                    ))
        if artifacts.teaching_cards:
            for i, tc in enumerate(artifacts.teaching_cards.get("teaching_cards", [])):
                for j, ref in enumerate(tc.get("evidence_refs", [])):
                    if ref and ref not in valid_refs:
                        findings.append(AuditFinding(
                            code="F-2",
                            severity="P0",
                            effect="BLOCK",
                            message=f"teaching_cards[{i}].evidence_refs[{j}] '{ref}' not found in evidence sources",
                            artifact="teaching_cards",
                            field=f"teaching_cards[{i}].evidence_refs[{j}]",
                        ))

        return findings

    def _check_refs_in_card(
        self,
        card: dict,
        valid_refs: set[str],
        artifact_name: str,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        ref_fields = [
            "problem", "core_idea", "method_overview",
            "experiment_summary", "limitations", "bottleneck",
        ]
        for field_name in ref_fields:
            field_val = card.get(field_name)
            if not isinstance(field_val, dict):
                continue
            ref = field_val.get("evidence_ref", "")
            if ref and ref not in valid_refs:
                findings.append(AuditFinding(
                    code="F-2",
                    severity="P0",
                    effect="BLOCK",
                    message=f"{artifact_name}.{field_name}.evidence_ref '{ref}' not found in evidence sources",
                    artifact=artifact_name,
                    field=f"{field_name}.evidence_ref",
                ))
        return findings

    def _extract_paper_id(self, artifacts: ArtifactBundle) -> str:
        if artifacts.understanding_status:
            pid = artifacts.understanding_status.get("paper_id", "")
            if pid:
                return pid
        if artifacts.paper_card:
            pid = artifacts.paper_card.get("paper_id", "")
            if pid:
                return pid
        if artifacts.evidence_index:
            pid = artifacts.evidence_index.get("paper_id", "")
            if pid:
                return pid
        return "unknown"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = [t for t in self._tokens(left) if t not in _STOPWORDS]
        right_tokens = [t for t in self._tokens(right) if t not in _STOPWORDS]
        if not left_tokens or not right_tokens:
            return 0.0
        left_set = set(left_tokens)
        right_set = set(right_tokens)
        return len(left_set & right_set) / max(1, min(len(left_set), len(right_set)))

    @staticmethod
    def _formula_char_ratio(text: str) -> float:
        stripped = text.strip()
        if not stripped:
            return 0.0
        formula_chars = sum(1 for c in stripped if c in "=\\_^{}$|/[]()+-*<>∑√αβγθλμσ")
        return formula_chars / len(stripped)

    @staticmethod
    def _float(value: object, default: float) -> float:
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return default

    def _looks_generic(self, text: str, paper_terms: set[str]) -> bool:
        tokens = [t for t in self._tokens(text) if t not in _STOPWORDS]
        if len(tokens) < 5:
            return False
        specific_hits = {t for t in tokens if t in paper_terms}
        if specific_hits:
            return False
        generic_count = sum(1 for t in tokens if t in _GENERIC_OUTPUT_TERMS)
        return generic_count / max(1, len(tokens)) >= 0.45

    def _paper_specific_terms(self, artifacts: ArtifactBundle) -> set[str]:
        parts: list[str] = []
        if artifacts.paper_skeleton:
            parts.append(str(artifacts.paper_skeleton.get("title") or ""))
        if artifacts.paper_card:
            parts.append(str(artifacts.paper_card.get("title") or ""))
        for claim in (artifacts.claim_evidence or {}).get("claims", [])[:20]:
            parts.append(str(claim.get("claim_text") or claim.get("quote_or_summary") or ""))
        for claim in (artifacts.evidence_index or {}).get("claims", [])[:20]:
            parts.append(str(claim.get("claim_text") or claim.get("quote_or_summary") or ""))
        terms = {
            token for text in parts for token in self._tokens(text)
            if token not in _STOPWORDS and token not in _GENERIC_OUTPUT_TERMS and len(token) >= 4
        }
        return terms

    def _evidence_text_by_ref(self, artifacts: ArtifactBundle) -> dict[str, str]:
        by_ref: dict[str, list[str]] = {}
        for claim in (artifacts.claim_evidence or {}).get("claims", []):
            ref = str(claim.get("evidence_ref") or "")
            if ref:
                by_ref.setdefault(ref, []).append(
                    str(claim.get("quote_or_summary") or claim.get("source_sentence") or claim.get("claim_text") or "")
                )
        for claim in (artifacts.evidence_index or {}).get("claims", []):
            ref = str(claim.get("evidence_ref") or "")
            if ref:
                by_ref.setdefault(ref, []).append(
                    str(claim.get("quote_or_summary") or claim.get("claim_text") or "")
                )
        return {ref: " ".join(texts) for ref, texts in by_ref.items()}

    def _survey_valid_sources(self, artifacts: ArtifactBundle) -> tuple[set[str], set[str]]:
        valid_refs: set[str] = set()
        valid_passages: set[str] = set()
        for passage in (artifacts.passage_index or {}).get("passages", []):
            passage_id = str(passage.get("passage_id") or "")
            if passage_id:
                valid_passages.add(passage_id)
            for evidence_ref in passage.get("evidence_refs", []):
                if evidence_ref:
                    valid_refs.add(str(evidence_ref))
        for claim in (artifacts.claim_evidence or {}).get("claims", []):
            evidence_ref = str(claim.get("evidence_ref") or "")
            passage_id = str(claim.get("passage_id") or "")
            if evidence_ref:
                valid_refs.add(evidence_ref)
            if passage_id:
                valid_passages.add(passage_id)
        return valid_refs, valid_passages

    def _iter_card_refs(self, artifacts: ArtifactBundle) -> list[tuple[str, str, str]]:
        refs: list[tuple[str, str, str]] = []
        if artifacts.paper_card:
            for field in ("problem", "core_idea", "method_overview", "experiment_summary", "limitations", "bottleneck"):
                value = artifacts.paper_card.get(field)
                if isinstance(value, dict) and value.get("evidence_ref"):
                    refs.append(("paper_card", f"{field}.evidence_ref", str(value["evidence_ref"])))
        if artifacts.formula_cards:
            for i, card in enumerate(artifacts.formula_cards.get("formula_cards", [])):
                if card.get("evidence_ref"):
                    refs.append(("formula_cards", f"formula_cards[{i}].evidence_ref", str(card["evidence_ref"])))
        if artifacts.teaching_cards:
            for i, card in enumerate(artifacts.teaching_cards.get("teaching_cards", [])):
                for j, ref in enumerate(card.get("evidence_refs", [])):
                    if ref:
                        refs.append(("teaching_cards", f"teaching_cards[{i}].evidence_refs[{j}]", str(ref)))
        return refs
