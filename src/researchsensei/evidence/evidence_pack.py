from __future__ import annotations

import re

from researchsensei.evidence.retriever import EvidenceRetriever
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.evidence import (
    ClaimEvidenceBundle,
    EvidencePack,
    EvidencePackItem,
    PassageIndex,
)

CLAIM_TYPE_PRIORITY = [
    "METHOD",
    "RESULT",
    "FORMULA_CONTEXT",
    "PROBLEM",
    "CONTRIBUTION",
    "LIMITATION",
    "DEFINITION",
]


def build_evidence_pack(
    claim_bundle: ClaimEvidenceBundle,
    passage_index: PassageIndex,
    retriever: EvidenceRetriever | None = None,
    *,
    max_total_tokens: int = 4000,
    max_items_per_type: int = 3,
    max_formula_items: int = 5,
    max_passage_chars: int = 500,
) -> EvidencePack:
    paper_id = claim_bundle.paper_id
    warnings: list[WarningItem] = []
    items: list[EvidencePackItem] = []
    total_tokens = 0

    # Build passage lookup
    passage_map = {p.passage_id: p for p in passage_index.passages}

    # Filter claims
    filtered = [
        c for c in claim_bundle.claims
        if c.semantic_support != "INSUFFICIENT_EVIDENCE"
        and c.confidence >= 0.3
        and c.claim_type
    ]

    # Group by claim_type
    by_type: dict[str, list] = {}
    for claim in filtered:
        by_type.setdefault(claim.claim_type, []).append(claim)

    if "FORMULA_CONTEXT" in by_type:
        by_type["FORMULA_CONTEXT"] = sorted(
            by_type["FORMULA_CONTEXT"],
            key=_formula_core_score,
            reverse=True,
        )

    # Process by priority
    budget_exceeded = False
    for claim_type in CLAIM_TYPE_PRIORITY:
        claims_of_type = by_type.get(claim_type, [])
        max_for_type = max_formula_items if claim_type == "FORMULA_CONTEXT" else max_items_per_type
        count = 0
        for claim in claims_of_type:
            if count >= max_for_type:
                break
            if budget_exceeded:
                break

            # Find supporting passage
            passage_text = ""
            retrieval_score = 0.0
            evidence_ref = claim.evidence_ref
            passage_id = claim.passage_id

            if retriever is not None and claim.claim_type != "FORMULA_CONTEXT":
                results = retriever.retrieve(claim.claim_text, passage_index)
                if results:
                    top = results[0]
                    passage_id = top.passage_id
                    retrieval_score = top.score
                    if top.evidence_ref:
                        evidence_ref = top.evidence_ref
                    passage = passage_map.get(top.passage_id)
                    if passage:
                        passage_text = passage.text
                else:
                    # Retriever no hit: fall back to claim.passage_id
                    passage = passage_map.get(claim.passage_id)
                    if passage:
                        passage_text = passage.text
            else:
                passage = passage_map.get(claim.passage_id)
                if passage:
                    passage_text = passage.text

            if not passage_text:
                warnings.append(WarningItem(
                    code="MISSING_PASSAGE",
                    message=f"No passage found for claim {claim.claim_id} (passage_id={claim.passage_id}).",
                ))
                continue

            # Truncate
            if len(passage_text) > max_passage_chars:
                passage_text = passage_text[:max_passage_chars]

            token_count = len(passage_text.split())

            # Check budget AFTER computing token_count
            if total_tokens + token_count > max_total_tokens:
                warnings.append(WarningItem(
                    code="TOKEN_BUDGET_EXCEEDED",
                    message=f"Token budget ({max_total_tokens}) exceeded, remaining items skipped.",
                ))
                budget_exceeded = True
                break

            total_tokens += token_count

            items.append(EvidencePackItem(
                claim_id=claim.claim_id,
                claim_type=claim.claim_type,
                evidence_ref=evidence_ref,
                passage_id=passage_id,
                quote_or_summary=claim.quote_or_summary,
                passage_text=passage_text,
                confidence=claim.confidence,
                retrieval_score=retrieval_score,
                token_count=token_count,
                source_artifact="claim_evidence",
                formula_origin=claim.formula_origin,
                formula_id=claim.formula_id,
                formula_page=claim.formula_page,
                formula_bbox=claim.formula_bbox,
                formula_ocr_status=claim.formula_ocr_status,
                equation_number=claim.equation_number,
                equation_group_id=claim.equation_group_id,
                group_order=claim.group_order,
                group_crop_path=claim.group_crop_path,
                group_overlay_path=claim.group_overlay_path,
                block_source=claim.block_source,
                risk_flags=list(claim.risk_flags),
            ))
            count += 1
        if budget_exceeded:
            break

    if not items:
        warnings.append(WarningItem(
            code="EMPTY_EVIDENCE_PACK",
            message="No items could be included in the evidence pack.",
        ))

    return EvidencePack(
        paper_id=paper_id,
        items=items,
        warnings=warnings,
        total_tokens=total_tokens,
    )


_CORE_FORMULA_KEYWORDS = {
    "attention": 6.0,
    "multihead": 5.0,
    "multi-head": 5.0,
    "softmax": 4.0,
    "transformer": 3.5,
    "edgeconv": 5.0,
    "relu": 2.0,
    "time2vec": 4.0,
    "t2v": 4.0,
    "loss": 4.0,
    "mse": 4.0,
    "reconstruction error": 4.0,
    "anomaly score": 6.0,
    "scoring function": 5.0,
    "gaussian": 3.0,
    "threshold": 2.0,
    "precision": 2.0,
    "recall": 2.0,
    "f1": 2.0,
}


def _formula_core_score(claim) -> float:
    """Rank formula evidence for M2 deep explanation.

    The score is intentionally heuristic and evidence-local: it uses only the
    formula text/context carried by M1/M2 artifacts, not external knowledge.
    """
    text = " ".join(
        str(getattr(claim, attr, "") or "")
        for attr in ("claim_text", "source_sentence", "quote_or_summary", "section")
    ).lower()
    score = 0.0
    for keyword, weight in _CORE_FORMULA_KEYWORDS.items():
        if keyword in text:
            score += weight
    section = str(getattr(claim, "section", "") or "").lower()
    if section == "method":
        score += 2.0
    elif section == "experiments":
        score += 1.5
    if "context before:" in text and "unknown" not in text:
        score += 1.0
    if "context after:" in text and "unknown" not in text:
        score += 0.5
    if re.search(r"\\tag\{?\d+", text):
        score += 0.5
    if _looks_like_formula_where_clause(text):
        score -= 8.0
    if str(getattr(claim, "formula_origin", "") or "") in {"source_latex", "mineru_latex", "parser_latex"}:
        score += 0.5
    risk_flags = [str(item).upper() for item in getattr(claim, "risk_flags", [])]
    if any("RAW" in flag or "UNKNOWN" in flag for flag in risk_flags):
        score -= 3.0
    return score


def _looks_like_formula_where_clause(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text.lower())
    if re.search(r"(?:^|formula:\s*)(?:w\s*h\s*e\s*r\s*e|where)\\?quad", compact):
        return True
    if re.search(r"(?:^|formula:\s*)(?:w\s*h\s*e\s*r\s*e|where)\b", compact):
        return True
    return " where " in compact and "formula:" in compact and compact.find("where") < compact.find("context before:")
