from __future__ import annotations

from datetime import datetime, timezone

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

        # Run checks
        evidence_findings = self._check_evidence_chain(artifacts)
        status_findings = self._check_status_gate(artifacts)
        card_ref_findings = self._check_card_refs(artifacts)

        findings.extend(evidence_findings)
        findings.extend(status_findings)
        findings.extend(card_ref_findings)

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

        # F-6: ClaimEvidenceV2.passage_id not in PassageIndex
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
            if downstream.get("advisor_questions") is not False:
                findings.append(AuditFinding(
                    code="F-5",
                    severity="P1",
                    effect="BLOCK",
                    message="DEGRADED_STRUCTURAL but allowed_downstream.advisor_questions is not False",
                    artifact="understanding_status",
                    field="allowed_downstream.advisor_questions",
                ))

        return findings

    # ------------------------------------------------------------------
    # Card ref checks
    # ------------------------------------------------------------------

    def _check_card_refs(self, artifacts: ArtifactBundle) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        # Collect all valid evidence_refs
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
            return findings

        # F-1: core paper_card fields missing evidence_ref
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
                        findings.append(AuditFinding(
                            code="F-1",
                            severity="P0",
                            effect="BLOCK",
                            message=f"paper_card.{field_name} has no evidence_ref",
                            artifact="paper_card",
                            field=f"{field_name}.evidence_ref",
                        ))

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
