from __future__ import annotations

import re
from typing import Any

from researchsensei.schemas.document import DocumentIngestion
from researchsensei.schemas.evidence import ClaimEvidenceBundle, Passage, PassageIndex


_SURVEY_TITLE_RE = re.compile(
    r"\b(survey|review|tutorial|systematic literature review|comprehensive review)\b",
    re.IGNORECASE,
)
_SURVEY_ABSTRACT_RE = re.compile(
    r"\b(this\s+(survey|review|tutorial)|we\s+(survey|review|summarize|present\s+an\s+overview)|"
    r"comprehensive\s+(survey|review)|systematic\s+literature\s+review)\b",
    re.IGNORECASE,
)
_TAXONOMY_RE = re.compile(
    r"\b(taxonom\w+|classif\w+|categor\w+|famil(?:y|ies)|approaches|methods|techniques|paradigms)\b",
    re.IGNORECASE,
)
_KEY_PAPER_RE = re.compile(
    r"(\[[0-9,\-\s;]+\]|\b[A-Z][A-Za-z\-]+ et al\.,?\s*\d{4}\b)",
    re.IGNORECASE,
)
_KEY_PAPER_CONTEXT_RE = re.compile(
    r"\b(key|representative|seminal|pioneering|early|classic|widely used|proposed|introduced|developed)\b",
    re.IGNORECASE,
)
_SURVEY_CLAIM_RE = re.compile(
    r"\b(we\s+(survey|review|summarize|compare|discuss|cover|organize)|this\s+(survey|review|tutorial)\s+"
    r"(summarizes|reviews|discusses|covers|organizes)|provide\s+(an\s+)?overview)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def build_survey_artifacts(
    document: DocumentIngestion,
    passage_index: PassageIndex,
    claim_evidence: ClaimEvidenceBundle,
) -> dict[str, dict[str, Any]]:
    """Build evidence-bound survey artifacts from M1/M2 canonical evidence only."""
    survey_signal = _detect_survey_signal(document, passage_index)
    paper_id = document.paper_id
    if not survey_signal["is_survey"]:
        return _not_applicable(paper_id, survey_signal["reason"])

    taxonomy = _extract_taxonomy(passage_index)
    key_papers = _extract_key_papers(passage_index)
    survey_claims = _extract_survey_claims(passage_index, taxonomy, key_papers)
    if not survey_claims:
        survey_claims = _claims_from_existing_evidence(claim_evidence)

    trusted = bool(taxonomy)
    status = "PASS" if trusted else "DEGRADED"
    reason = "" if trusted else "NO_TAXONOMY_EVIDENCE"
    landscape_summary = _first_text(survey_claims) or _first_taxonomy_text(taxonomy) or "INSUFFICIENT_EVIDENCE"

    survey_status = {
        "schema_version": "m2_survey",
        "paper_id": paper_id,
        "is_survey": True,
        "status": status,
        "reason": reason,
        "source_confidence": survey_signal["source_confidence"],
        "signal_evidence_ref": survey_signal.get("evidence_ref", ""),
        "signal_passage_id": survey_signal.get("passage_id", ""),
    }
    survey_landscape = {
        "schema_version": "m2_survey",
        "paper_id": paper_id,
        "trusted": trusted,
        "status": status,
        "summary": landscape_summary,
        "method_family_count": len(taxonomy),
        "key_paper_count": len(key_papers),
        "evidence_refs": _unique([item.get("evidence_ref", "") for item in taxonomy + survey_claims]),
    }
    method_taxonomy = {
        "schema_version": "m2_survey",
        "paper_id": paper_id,
        "taxonomy": taxonomy,
    }
    extracted_key_papers = {
        "schema_version": "m2_survey",
        "paper_id": paper_id,
        "papers": key_papers,
    }
    survey_claim_bundle = {
        "schema_version": "m2_survey",
        "paper_id": paper_id,
        "claims": survey_claims,
    }
    return {
        "survey_status": survey_status,
        "survey_landscape": survey_landscape,
        "method_taxonomy": method_taxonomy,
        "extracted_key_papers": extracted_key_papers,
        "survey_claims": survey_claim_bundle,
    }


def _not_applicable(paper_id: str, reason: str) -> dict[str, dict[str, Any]]:
    return {
        "survey_status": {
            "schema_version": "m2_survey",
            "paper_id": paper_id,
            "is_survey": False,
            "status": "NOT_APPLICABLE",
            "reason": reason,
            "source_confidence": "none",
            "signal_evidence_ref": "",
            "signal_passage_id": "",
        },
        "survey_landscape": {
            "schema_version": "m2_survey",
            "paper_id": paper_id,
            "trusted": False,
            "status": "NOT_APPLICABLE",
            "summary": "",
            "method_family_count": 0,
            "key_paper_count": 0,
            "evidence_refs": [],
        },
        "method_taxonomy": {
            "schema_version": "m2_survey",
            "paper_id": paper_id,
            "taxonomy": [],
        },
        "extracted_key_papers": {
            "schema_version": "m2_survey",
            "paper_id": paper_id,
            "papers": [],
        },
        "survey_claims": {
            "schema_version": "m2_survey",
            "paper_id": paper_id,
            "claims": [],
        },
    }


def _detect_survey_signal(document: DocumentIngestion, passage_index: PassageIndex) -> dict[str, Any]:
    title = " ".join(block.text for block in document.blocks if block.type.value == "title")
    if _SURVEY_TITLE_RE.search(title):
        return {"is_survey": True, "source_confidence": "high", "reason": "TITLE_SIGNAL"}

    for passage in passage_index.passages[:6]:
        section = passage.section.lower()
        if section in {"abstract", "introduction", "intro", "unknown"} and _SURVEY_ABSTRACT_RE.search(passage.text):
            return {
                "is_survey": True,
                "source_confidence": "medium",
                "reason": "ABSTRACT_SIGNAL",
                "evidence_ref": passage.evidence_refs[0] if passage.evidence_refs else "",
                "passage_id": passage.passage_id,
            }
    return {"is_survey": False, "reason": "NO_SURVEY_SIGNAL"}


def _extract_taxonomy(passage_index: PassageIndex) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for passage in passage_index.passages:
        if passage.section.lower() == "references":
            continue
        for sentence in _sentences(passage.text):
            if not _TAXONOMY_RE.search(sentence):
                continue
            label = _family_label(sentence)
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "method_family": label,
                "description": sentence,
                "evidence_ref": passage.evidence_refs[0] if passage.evidence_refs else "",
                "passage_id": passage.passage_id,
                "source_section": passage.section,
                "confidence": 0.65,
            })
            if len(items) >= 8:
                return items
    return items


def _extract_key_papers(passage_index: PassageIndex) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for passage in passage_index.passages:
        if passage.section.lower() == "references":
            continue
        for sentence in _sentences(passage.text):
            if not _KEY_PAPER_RE.search(sentence):
                continue
            if not _KEY_PAPER_CONTEXT_RE.search(sentence):
                continue
            label = _paper_label(sentence)
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            papers.append({
                "paper_label": label,
                "context": sentence,
                "evidence_ref": passage.evidence_refs[0] if passage.evidence_refs else "",
                "passage_id": passage.passage_id,
                "source_section": passage.section,
                "confidence": 0.55,
            })
            if len(papers) >= 12:
                return papers
    return papers


def _extract_survey_claims(
    passage_index: PassageIndex,
    taxonomy: list[dict[str, Any]],
    key_papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    counter = 0
    for passage in passage_index.passages:
        if passage.section.lower() == "references":
            continue
        for sentence in _sentences(passage.text):
            if not _SURVEY_CLAIM_RE.search(sentence):
                continue
            counter += 1
            claims.append(_survey_claim(counter, "SURVEY_SCOPE", sentence, passage))
            if counter >= 8:
                break
        if counter >= 8:
            break

    for item in taxonomy[:5]:
        counter += 1
        claims.append({
            "claim_id": f"survey:claim:{counter:03d}",
            "claim_type": "METHOD_TAXONOMY",
            "claim_text": item["description"],
            "evidence_ref": item["evidence_ref"],
            "passage_id": item["passage_id"],
            "section": item["source_section"],
            "confidence": item["confidence"],
        })
    for item in key_papers[:5]:
        counter += 1
        claims.append({
            "claim_id": f"survey:claim:{counter:03d}",
            "claim_type": "KEY_PAPER",
            "claim_text": item["context"],
            "evidence_ref": item["evidence_ref"],
            "passage_id": item["passage_id"],
            "section": item["source_section"],
            "confidence": item["confidence"],
        })
    return claims


def _claims_from_existing_evidence(claim_evidence: ClaimEvidenceBundle) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for index, claim in enumerate(claim_evidence.claims[:5], start=1):
        claims.append({
            "claim_id": f"survey:claim:{index:03d}",
            "claim_type": "SURVEY_CONTEXT",
            "claim_text": claim.claim_text,
            "evidence_ref": claim.evidence_ref,
            "passage_id": claim.passage_id,
            "section": claim.section,
            "confidence": min(float(claim.confidence), 0.5),
        })
    return claims


def _survey_claim(counter: int, claim_type: str, sentence: str, passage: Passage) -> dict[str, Any]:
    return {
        "claim_id": f"survey:claim:{counter:03d}",
        "claim_type": claim_type,
        "claim_text": sentence,
        "evidence_ref": passage.evidence_refs[0] if passage.evidence_refs else "",
        "passage_id": passage.passage_id,
        "section": passage.section,
        "confidence": 0.6,
    }


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(text) if len(sentence.strip()) >= 40]


def _family_label(sentence: str) -> str:
    clean = " ".join(sentence.split())
    match = re.search(r"([A-Za-z][A-Za-z0-9\- ]{2,80})\s+(methods|approaches|techniques|models|paradigms|families)", clean)
    if match:
        return match.group(0).strip().rstrip(".,;:")
    return clean[:80].strip().rstrip(".,;:") or "survey method family"


def _paper_label(sentence: str) -> str:
    citation = _KEY_PAPER_RE.search(sentence)
    if citation:
        return citation.group(0).strip()
    return " ".join(sentence.split())[:80].strip().rstrip(".,;:")


def _first_text(claims: list[dict[str, Any]]) -> str:
    for claim in claims:
        text = str(claim.get("claim_text") or "").strip()
        if text:
            return text
    return ""


def _first_taxonomy_text(taxonomy: list[dict[str, Any]]) -> str:
    for item in taxonomy:
        text = str(item.get("description") or "").strip()
        if text:
            return text
    return ""


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
