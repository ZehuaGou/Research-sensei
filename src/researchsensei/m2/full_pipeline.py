from __future__ import annotations

import asyncio
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.evidence.claim_extractor import build_claim_evidence
from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.formula_card import build_formula_cards
from researchsensei.formula_card_v2 import build_formula_cards_v2
from researchsensei.grounding import build_evidence_index
from researchsensei.llm.client import LLMClient
from researchsensei.m2.artifact_reader import M1ArtifactBundle, M1ArtifactReader
from researchsensei.paper_card import build_paper_card
from researchsensei.paper_card_v2 import build_paper_card_v2
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import (
    ArtifactBundle,
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    DownstreamGates,
    EvidencePack,
    EvidenceType,
    FormulaCardBundle,
    QualityReport,
    SourceStatus,
    TeachingCardBundle,
    UnderstandingStatus,
    WarningItem,
)
from researchsensei.schemas.status import EvidencePackSummary
from researchsensei.teaching_card import build_teaching_cards
from researchsensei.teaching_card_v2 import build_teaching_cards_v2
from researchsensei.workspace.store import to_plain_data


SUPPRESSED_M1_RISK_FLAGS = {
    "PAGE_HEADER_REPEATED",
    "PAGE_NUMBER_FOOTER",
    "AUTHOR_FOOTER",
    "FUNDING_NOTE",
    "FRONT_MATTER_AFFILIATION",
}


@dataclass(frozen=True)
class M2FullRunResult:
    paper_id: str
    output_dir: Path
    status: UnderstandingStatus
    quality_report: QualityReport
    run_summary: dict[str, Any]


def run_m2_full_pipeline(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    llm_client: LLMClient | None = None,
    llm_metadata: dict[str, Any] | None = None,
) -> M2FullRunResult:
    """Run the full M2.1-M2.5 chain from an M1 canonical artifact bundle."""
    started = time.perf_counter()
    reader = M1ArtifactReader(input_dir)
    bundle = reader.load()
    output = Path(output_dir)
    _reset_output_dir(output)

    paper_id = str(bundle.front_matter.get("paper_id") or bundle.paper_metadata.get("paper_id") or bundle.input_dir.name)
    document = build_document_from_m1_bundle(bundle, paper_id=paper_id)
    source_status = _source_status(bundle)
    canonical_status = _canonical_status(bundle)

    passage_index = build_passage_index(document)
    claim_evidence = build_claim_evidence(document, passage_index)
    evidence_index = build_evidence_index(document)
    paper_skeleton = build_paper_skeleton(document, evidence_index)
    evidence_pack = build_evidence_pack(claim_evidence, passage_index, None)
    evidence_pack_summary = _evidence_pack_summary(evidence_pack, claim_evidence)

    card_artifacts: dict[str, Any] = {}
    status = _preflight_status(
        paper_id=paper_id,
        bundle=bundle,
        document=document,
        passage_index=passage_index,
        claim_evidence=claim_evidence,
        evidence_pack=evidence_pack,
        evidence_pack_summary=evidence_pack_summary,
        llm_client=llm_client,
    )

    if status is None:
        if llm_client is None:
            paper_card = build_paper_card(paper_skeleton, evidence_index)
            formula_cards = build_formula_cards(document, evidence_index, paper_skeleton)
            teaching_cards = build_teaching_cards(paper_card, formula_cards, paper_skeleton, evidence_index)
            card_artifacts = {
                "paper_card": paper_card,
                "formula_cards": formula_cards,
                "teaching_cards": teaching_cards,
            }
            status = _baseline_status(paper_id, evidence_pack_summary)
        else:
            card_artifacts, status = _build_llm_cards(
                paper_id=paper_id,
                bundle=bundle,
                evidence_pack=evidence_pack,
                paper_skeleton=paper_skeleton,
                evidence_pack_summary=evidence_pack_summary,
                llm_client=llm_client,
            )

    quality_report, status, card_artifacts = _audit_candidate(
        paper_id=paper_id,
        status=status,
        card_artifacts=card_artifacts,
        evidence_index=evidence_index,
        claim_evidence=claim_evidence,
        passage_index=passage_index,
        paper_skeleton=paper_skeleton,
    )

    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "source_status.json", source_status)
    _write_json(output / "canonical_status.json", canonical_status)
    _write_json(output / "parsed_document.json", document)
    _write_json(output / "passage_index.json", passage_index)
    _write_json(output / "claim_evidence.json", claim_evidence)
    _write_json(output / "evidence_index.json", evidence_index)
    _write_json(output / "paper_skeleton.json", paper_skeleton)
    _write_json(output / "evidence_pack.json", evidence_pack)
    if "paper_card" in card_artifacts:
        _write_json(output / "paper_card.json", card_artifacts["paper_card"])
    if "formula_cards" in card_artifacts:
        _write_json(output / "formula_cards.json", card_artifacts["formula_cards"])
    if "teaching_cards" in card_artifacts:
        _write_json(output / "teaching_cards.json", card_artifacts["teaching_cards"])
    _write_json(output / "quality_report.json", quality_report)
    _write_json(output / "understanding_status.json", status)

    current_hashes = reader.hash_required_inputs()
    runtime_seconds = round(time.perf_counter() - started, 3)
    run_summary = {
        "schema_version": "m2_full_v1",
        "paper_id": paper_id,
        "title": paper_skeleton.title,
        "input_dir": str(bundle.input_dir),
        "output_dir": str(output),
        "status": status.status,
        "blocking_reason": status.blocking_reason,
        "m1_contract_status": bundle.contract.get("status"),
        "m1_canonical_quality_status": bundle.front_matter.get("canonical_quality_status", ""),
        "m1_m2_ready": bool(bundle.front_matter.get("m2_ready", False)),
        "m1_formula_m2_ready": bool(bundle.front_matter.get("m2_ready_for_formula_understanding", True)),
        "m1_artifacts_modified": current_hashes != bundle.input_hashes,
        "document_block_count": len(document.blocks),
        "passage_count": len(passage_index.passages),
        "claim_count": len(claim_evidence.claims),
        "evidence_pack_count": len(evidence_pack.items),
        "formula_count": len([b for b in document.blocks if b.type == BlockType.FORMULA]),
        "llm_enabled": llm_client is not None,
        "llm_metadata": _llm_metadata(llm_client, llm_metadata or {}),
        "runtime_seconds": runtime_seconds,
        "output_artifacts": sorted(path.name for path in output.iterdir() if path.is_file()),
    }
    _write_json(output / "m2_run_summary.json", run_summary)
    (output / "m2_full_report.md").write_text(_render_report(run_summary, quality_report, status), encoding="utf-8")

    return M2FullRunResult(
        paper_id=paper_id,
        output_dir=output,
        status=status,
        quality_report=quality_report,
        run_summary=run_summary,
    )


def build_document_from_m1_bundle(bundle: M1ArtifactBundle, *, paper_id: str) -> DocumentIngestion:
    """Convert M1 canonical blocks/slots into evidence-ready DocumentIngestion."""
    slots_by_block = {
        str(slot.get("block_id") or ""): slot
        for slot in bundle.formula_slots
        if str(slot.get("block_id") or "")
    }
    blocks: list[DocumentBlock] = []
    warnings = _document_warnings(bundle)
    skipped_layout = 0

    for raw_block in bundle.document_blocks:
        risk_flags = [str(item) for item in raw_block.get("risk_flags", [])]
        if _is_suppressed_layout_block(raw_block, risk_flags):
            skipped_layout += 1
            continue
        block_id = str(raw_block.get("block_id") or f"b{len(blocks) + 1:04d}")
        block_type = _map_block_type(raw_block, is_first_block=not blocks)
        slot = slots_by_block.get(block_id, {}) if block_type == BlockType.FORMULA else {}
        block = _document_block(
            paper_id=paper_id,
            raw_block=raw_block,
            block_id=block_id,
            block_type=block_type,
            slot=slot,
            risk_flags=risk_flags,
        )
        if block.text.strip():
            blocks.append(block)

    if skipped_layout:
        warnings.append(WarningItem(
            code="M1_LAYOUT_BLOCKS_SUPPRESSED",
            message=f"Suppressed {skipped_layout} M1 page header/footer/front-matter blocks before M2 evidence.",
        ))

    return DocumentIngestion(
        paper_id=paper_id,
        detected_language="unknown",
        source_path=str(bundle.input_dir / "canonical_paper.md"),
        parser_name="m1_canonical_bundle",
        degraded=any(w.code.startswith("M1_") for w in warnings),
        warnings=warnings,
        blocks=blocks,
    )


def _document_block(
    *,
    paper_id: str,
    raw_block: dict[str, Any],
    block_id: str,
    block_type: BlockType,
    slot: dict[str, Any],
    risk_flags: list[str],
) -> DocumentBlock:
    section = str(raw_block.get("section") or slot.get("section") or "")
    page = _int_or_none(raw_block.get("page") or slot.get("page"))
    bbox = _bbox(raw_block.get("bbox") or slot.get("bbox"))
    latex = str(slot.get("final_latex") or raw_block.get("latex") or raw_block.get("text") or "").strip()
    formula_id = str(slot.get("formula_id") or "")
    if block_type == BlockType.FORMULA:
        text = _formula_text(slot=slot, raw_latex=latex)
    else:
        text = str(raw_block.get("text") or "").strip()
    return DocumentBlock(
        block_id=block_id,
        type=block_type,
        text=text,
        evidence_ref=f"{paper_id}:{block_id}",
        section=section,
        page=page,
        normalized_text=" ".join(text.lower().split()),
        raw_latex=latex if block_type == BlockType.FORMULA else "",
        bbox=bbox,
        formula_id=formula_id,
        formula_latex=latex if block_type == BlockType.FORMULA else "",
        formula_origin=str(slot.get("final_origin") or raw_block.get("formula_origin") or ""),
        formula_bbox=bbox if block_type == BlockType.FORMULA else None,
        formula_page=page if block_type == BlockType.FORMULA else None,
        formula_context_before=str(slot.get("nearby_text_before") or ""),
        formula_context_after=str(slot.get("nearby_text_after") or ""),
        formula_ocr_status=str(slot.get("formula_ocr_status") or slot.get("ocr_status") or "not_required"),
        formula_explanation_status=_formula_explanation_status(str(slot.get("final_origin") or "")),
        block_source=str(slot.get("block_source") or raw_block.get("source") or ""),
        section_confidence=str(slot.get("section_confidence") or raw_block.get("section_confidence") or ""),
        risk_flags=risk_flags + [str(item) for item in slot.get("risk_flags", []) if str(item) not in risk_flags],
        crop_path=str(slot.get("crop_path") or ""),
        overlay_path=str(slot.get("overlay_path") or ""),
        parse_quality_status=str(slot.get("parse_quality_status") or ""),
        fallback_used=bool(slot.get("fallback_used", False)),
        llama_refined=bool(slot.get("llama_refined", False)),
        mineru_available=str(slot.get("block_source") or raw_block.get("source") or "") == "mineru25pro",
        structure_audit_status=str(slot.get("structure_audit_status") or ""),
    )


def _formula_text(*, slot: dict[str, Any], raw_latex: str) -> str:
    formula_id = str(slot.get("formula_id") or "formula")
    before = str(slot.get("nearby_text_before") or "").strip()
    after = str(slot.get("nearby_text_after") or "").strip()
    origin = str(slot.get("final_origin") or "")
    return (
        f"Formula {formula_id}. Origin: {origin or 'unknown'}. "
        f"Formula: {raw_latex}. "
        f"Context before: {before or 'unknown'}. "
        f"Context after: {after or 'unknown'}."
    )


def _map_block_type(raw_block: dict[str, Any], *, is_first_block: bool) -> BlockType:
    raw_type = str(raw_block.get("block_type") or "").lower()
    section = str(raw_block.get("section") or "").lower()
    if raw_type == "formula":
        return BlockType.FORMULA
    if raw_type == "table":
        return BlockType.TABLE
    if raw_type == "figure":
        return BlockType.FIGURE
    if section == "references" or raw_type == "reference":
        return BlockType.REFERENCE
    if raw_type == "title":
        return BlockType.TITLE if is_first_block or section in {"", "unknown"} else BlockType.HEADING
    if section == "abstract":
        return BlockType.ABSTRACT
    return BlockType.PARAGRAPH


def _is_suppressed_layout_block(raw_block: dict[str, Any], risk_flags: list[str]) -> bool:
    if set(risk_flags).intersection(SUPPRESSED_M1_RISK_FLAGS):
        return True
    text = str(raw_block.get("text") or "").strip()
    block_type = str(raw_block.get("block_type") or "").lower()
    return block_type == "text" and text.isdigit() and len(text) <= 3


def _document_warnings(bundle: M1ArtifactBundle) -> list[WarningItem]:
    warnings: list[WarningItem] = []
    if bundle.contract.get("status") != "PASS":
        warnings.append(WarningItem(
            code="M1_CONTRACT_NOT_PASS",
            message="M1 artifact contract did not pass.",
            detail="; ".join(str(item) for item in bundle.contract.get("reasons", [])),
        ))
    if not bundle.front_matter.get("m2_ready", False):
        warnings.append(WarningItem(code="M1_M2_NOT_READY", message="M1 front matter has m2_ready=false."))
    quality_status = str(bundle.front_matter.get("canonical_quality_status") or "")
    if quality_status and quality_status != "PASS":
        warnings.append(WarningItem(
            code="M1_CANONICAL_QUALITY_NOT_PASS",
            message=f"M1 canonical_quality_status={quality_status}.",
        ))
    if not bundle.front_matter.get("m2_ready_for_formula_understanding", True):
        warnings.append(WarningItem(
            code="M1_FORMULA_UNDERSTANDING_NOT_READY",
            message="M1 marked formulas as not ready for downstream formula understanding.",
        ))
    return warnings


def _preflight_status(
    *,
    paper_id: str,
    bundle: M1ArtifactBundle,
    document: DocumentIngestion,
    passage_index,
    claim_evidence,
    evidence_pack: EvidencePack,
    evidence_pack_summary: EvidencePackSummary,
    llm_client: LLMClient | None,
) -> UnderstandingStatus | None:
    if bundle.contract.get("status") != "PASS":
        return _blocked_status(paper_id, "M1_CONTRACT_FAILED", evidence_pack_summary, document.warnings)
    if not bundle.front_matter.get("m2_ready", False):
        return _blocked_status(paper_id, "M1_M2_NOT_READY", evidence_pack_summary, document.warnings)
    if str(bundle.front_matter.get("canonical_quality_status") or "") == "FAIL":
        return _blocked_status(paper_id, "M1_CANONICAL_QUALITY_FAIL", evidence_pack_summary, document.warnings)
    if not passage_index.passages:
        return _blocked_status(paper_id, "NO_PASSAGES", evidence_pack_summary, passage_index.warnings)
    if not claim_evidence.claims:
        return _blocked_status(paper_id, "NO_CLAIMS", evidence_pack_summary, claim_evidence.warnings)
    if not evidence_pack.items:
        return _blocked_status(paper_id, "EMPTY_EVIDENCE_PACK", evidence_pack_summary, evidence_pack.warnings)
    if llm_client is not None and not any(item.claim_type == "METHOD" for item in evidence_pack.items):
        return _blocked_status(paper_id, "MISSING_METHOD_EVIDENCE", evidence_pack_summary)
    return None


def _build_llm_cards(
    *,
    paper_id: str,
    bundle: M1ArtifactBundle,
    evidence_pack: EvidencePack,
    paper_skeleton,
    evidence_pack_summary: EvidencePackSummary,
    llm_client: LLMClient,
) -> tuple[dict[str, Any], UnderstandingStatus]:
    try:
        paper_card = _run_async(build_paper_card_v2(evidence_pack, paper_skeleton, llm_client))
    except Exception as exc:
        return {}, _blocked_status(
            paper_id,
            "PAPER_CARD_V2_FAILED",
            evidence_pack_summary,
            [WarningItem(code="V2_BUILDER_FAILED", message=f"paper_card_v2: {exc}")],
        )

    formula_cards: FormulaCardBundle | None = None
    formula_ready = bool(bundle.front_matter.get("m2_ready_for_formula_understanding", True))
    if formula_ready:
        try:
            formula_cards = _run_async(build_formula_cards_v2(evidence_pack, paper_skeleton, llm_client))
        except Exception as exc:
            return {}, _blocked_status(
                paper_id,
                "FORMULA_CARDS_V2_FAILED",
                evidence_pack_summary,
                [WarningItem(code="V2_BUILDER_FAILED", message=f"formula_cards_v2: {exc}")],
            )
    else:
        formula_cards = FormulaCardBundle(
            paper_id=paper_id,
            formula_cards=[],
            warnings=["M1_FORMULA_UNDERSTANDING_NOT_READY"],
            evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
        )

    try:
        teaching_cards = _run_async(build_teaching_cards_v2(evidence_pack, paper_card, paper_skeleton, llm_client))
    except Exception as exc:
        card_artifacts = {"paper_card": paper_card, "formula_cards": formula_cards}
        return card_artifacts, _degraded_status(
            paper_id,
            formula_cards,
            evidence_pack_summary,
            [WarningItem(code="V2_BUILDER_FAILED", message=f"teaching_cards_v2: {exc}")],
        )

    card_artifacts = {
        "paper_card": paper_card,
        "formula_cards": formula_cards,
        "teaching_cards": teaching_cards,
    }
    if str(bundle.front_matter.get("canonical_quality_status") or "") == "DEGRADED" or not formula_ready:
        return card_artifacts, _degraded_status(paper_id, formula_cards, evidence_pack_summary, document_warnings_from_bundle(bundle))
    return card_artifacts, _success_status(paper_id, formula_cards, evidence_pack_summary)


def document_warnings_from_bundle(bundle: M1ArtifactBundle) -> list[WarningItem]:
    return _document_warnings(bundle)


def _audit_candidate(
    *,
    paper_id: str,
    status: UnderstandingStatus,
    card_artifacts: dict[str, Any],
    evidence_index,
    claim_evidence,
    passage_index,
    paper_skeleton,
) -> tuple[QualityReport, UnderstandingStatus, dict[str, Any]]:
    auditor = QualityAuditor()
    bundle = ArtifactBundle(
        paper_card=_to_dict(card_artifacts.get("paper_card")),
        formula_cards=_to_dict(card_artifacts.get("formula_cards")),
        teaching_cards=_to_dict(card_artifacts.get("teaching_cards")),
        evidence_index=_to_dict(evidence_index),
        claim_evidence=_to_dict(claim_evidence),
        passage_index=_to_dict(passage_index),
        paper_skeleton=_to_dict(paper_skeleton),
        understanding_status=_to_dict(status),
    )
    quality_report = auditor.audit(bundle)
    if status.status in {"SUCCESS", "DEGRADED_STRUCTURAL"} and any(f.effect == "BLOCK" for f in quality_report.findings):
        status = _blocked_status(
            paper_id,
            "AUDIT_BLOCKED",
            status.evidence_pack_summary,
            [
                WarningItem(
                    code=finding.code,
                    message=finding.message,
                    detail=f"artifact={finding.artifact}; field={finding.field}",
                )
                for finding in quality_report.findings
            ],
            llm_failed=False,
            audit_failed=True,
        )
        card_artifacts = {}
    return quality_report, status, card_artifacts


def _source_status(bundle: M1ArtifactBundle) -> SourceStatus:
    return SourceStatus(
        source_type="m1_canonical_bundle",
        original_input=str(bundle.input_dir),
        resolved_path=str(bundle.input_dir / "canonical_paper.md"),
        status="resolved",
        warnings=[str(item) for item in bundle.contract.get("reasons", [])],
        degraded_flags=[] if bundle.contract.get("status") == "PASS" else ["M1_CONTRACT_FAILED"],
        content_type="text/markdown",
        size_bytes=(bundle.input_dir / "canonical_paper.md").stat().st_size,
    )


def _canonical_status(bundle: M1ArtifactBundle) -> dict[str, Any]:
    return {
        "paper_id": bundle.front_matter.get("paper_id", ""),
        "title": bundle.front_matter.get("title", bundle.paper_metadata.get("title", "")),
        "canonical_quality_status": bundle.front_matter.get("canonical_quality_status", ""),
        "canonicalization_status": bundle.front_matter.get("canonicalization_status", ""),
        "m2_ready": bool(bundle.front_matter.get("m2_ready", False)),
        "m2_ready_for_formula_understanding": bool(bundle.front_matter.get("m2_ready_for_formula_understanding", True)),
        "primary_parser": bundle.front_matter.get("primary_parser", bundle.paper_metadata.get("primary_parser", "")),
        "input_contract": bundle.contract,
    }


def _baseline_status(paper_id: str, evidence_pack_summary: EvidencePackSummary) -> UnderstandingStatus:
    return UnderstandingStatus(
        schema_version="v2",
        paper_id=paper_id,
        status="BASELINE_ONLY",
        blocking_reason="NO_LLM_CLIENT",
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
        component_status={
            "paper_card": "BASELINE",
            "formula_cards": "BASELINE",
            "teaching_cards": "BASELINE",
            "llm": "SKIPPED",
            "evidence_pack": "SUCCESS",
            "audit": "PENDING",
        },
        checked_artifacts=_checked_artifacts(include_cards=True),
        evidence_pack_summary=evidence_pack_summary,
    )


def _success_status(
    paper_id: str,
    formula_cards: FormulaCardBundle,
    evidence_pack_summary: EvidencePackSummary,
) -> UnderstandingStatus:
    formula_status = "SKIPPED" if not formula_cards.formula_cards else "SUCCESS"
    return UnderstandingStatus(
        schema_version="v2",
        paper_id=paper_id,
        status="SUCCESS",
        allowed_for_user_display=True,
        allowed_downstream=DownstreamGates(
            reading_display=True,
            phase12_patterns=True,
            phase12_drill=True,
            advisor_questions=True,
        ),
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": formula_status,
            "teaching_cards": "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
            "audit": "SUCCESS",
        },
        checked_artifacts=_checked_artifacts(include_cards=True),
        evidence_pack_summary=evidence_pack_summary,
    )


def _degraded_status(
    paper_id: str,
    formula_cards: FormulaCardBundle,
    evidence_pack_summary: EvidencePackSummary,
    warnings: list[WarningItem] | None = None,
) -> UnderstandingStatus:
    formula_status = "SKIPPED" if not formula_cards.formula_cards else "SUCCESS"
    return UnderstandingStatus(
        schema_version="v2",
        paper_id=paper_id,
        status="DEGRADED_STRUCTURAL",
        blocking_reason="PARTIAL_M2_OUTPUT",
        warnings=warnings or [],
        allowed_for_user_display=True,
        allowed_downstream=DownstreamGates(
            reading_display=True,
            phase12_patterns=True,
            phase12_drill=True,
            phase12_drill_degraded=True,
            advisor_questions=False,
        ),
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": formula_status,
            "teaching_cards": "FAILED" if warnings else "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
            "audit": "SUCCESS",
        },
        checked_artifacts=_checked_artifacts(include_cards=True),
        evidence_pack_summary=evidence_pack_summary,
    )


def _blocked_status(
    paper_id: str,
    blocking_reason: str,
    evidence_pack_summary: EvidencePackSummary | None = None,
    warnings: list[WarningItem] | None = None,
    *,
    llm_failed: bool = True,
    audit_failed: bool = False,
) -> UnderstandingStatus:
    return UnderstandingStatus(
        schema_version="v2",
        paper_id=paper_id,
        status="BLOCKED_UNDERSTANDING",
        blocking_reason=blocking_reason,
        warnings=warnings or [],
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
        component_status={
            "paper_card": "FAILED" if llm_failed else "SKIPPED",
            "formula_cards": "SKIPPED",
            "teaching_cards": "SKIPPED",
            "llm": "FAILED" if llm_failed else "SUCCESS",
            "evidence_pack": "SUCCESS" if evidence_pack_summary else "FAILED",
            "audit": "FAILED" if audit_failed else "SKIPPED",
        },
        checked_artifacts=_checked_artifacts(include_cards=False),
        evidence_pack_summary=evidence_pack_summary,
    )


def _checked_artifacts(*, include_cards: bool) -> list[str]:
    artifacts = [
        "source_status",
        "canonical_status",
        "parsed_document",
        "passage_index",
        "claim_evidence",
        "evidence_index",
        "paper_skeleton",
        "evidence_pack",
        "understanding_status",
        "quality_report",
    ]
    if include_cards:
        artifacts.extend(["paper_card", "formula_cards", "teaching_cards"])
    return artifacts


def _evidence_pack_summary(evidence_pack: EvidencePack, claim_bundle) -> EvidencePackSummary:
    included = [item.claim_id for item in evidence_pack.items]
    included_set = set(included)
    excluded = [claim.claim_id for claim in claim_bundle.claims if claim.claim_id not in included_set]
    counts: dict[str, int] = {}
    for item in evidence_pack.items:
        counts[item.claim_type] = counts.get(item.claim_type, 0) + 1
    return EvidencePackSummary(
        included_claim_ids=included,
        excluded_claim_ids=excluded,
        total_tokens=evidence_pack.total_tokens,
        claim_type_counts=counts,
        truncated_passage_ids=[],
    )


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if hasattr(coro, "close"):
        coro.close()
    raise RuntimeError("run_m2_full_pipeline cannot execute async LLM builders inside an active event loop")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(to_plain_data(value), ensure_ascii=False, indent=2), encoding="utf-8")


def _to_dict(obj: object | None) -> dict | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return to_plain_data(obj)


def _reset_output_dir(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)


def _llm_metadata(llm_client: LLMClient | None, base: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(base)
    if llm_client is None:
        metadata.setdefault("provider", "none")
        metadata.setdefault("model", "")
        metadata.setdefault("call_count", 0)
        return metadata
    usage = getattr(llm_client, "usage", None)
    if usage is not None and hasattr(usage, "as_dict"):
        metadata["usage"] = usage.as_dict()
        metadata["call_count"] = usage.as_dict().get("call_count", 0)
    provider = getattr(llm_client, "provider", None) or getattr(getattr(llm_client, "client", None), "provider", None)
    if provider is not None:
        metadata.setdefault("provider", getattr(provider, "name", ""))
        metadata.setdefault("model", getattr(provider, "model", ""))
    return metadata


def _render_report(run_summary: dict[str, Any], quality_report: QualityReport, status: UnderstandingStatus) -> str:
    findings = "\n".join(
        f"- {finding.code}: {finding.effect} {finding.message}"
        for finding in quality_report.findings
    ) or "- none"
    return "\n".join(
        [
            "# M2 Full Pipeline Report",
            "",
            f"- paper_id: {run_summary['paper_id']}",
            f"- status: {status.status}",
            f"- blocking_reason: {status.blocking_reason or 'none'}",
            f"- llm_enabled: {run_summary['llm_enabled']}",
            f"- document_blocks: {run_summary['document_block_count']}",
            f"- passages: {run_summary['passage_count']}",
            f"- claims: {run_summary['claim_count']}",
            f"- evidence_pack_items: {run_summary['evidence_pack_count']}",
            f"- formulas: {run_summary['formula_count']}",
            "",
            "## Quality Findings",
            findings,
        ]
    )


def _formula_explanation_status(origin: str) -> str:
    if origin == "source_latex":
        return "source_exact"
    if origin in {"raw_formula_text", "unknown", "unresolved"}:
        return "degraded"
    return "parser_derived" if origin else ""


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        return tuple(float(item) for item in value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
