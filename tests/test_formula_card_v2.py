from __future__ import annotations

import asyncio

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.formula_card_v2 import build_formula_cards_v2
from researchsensei.schemas import ArtifactBundle, EvidencePack, EvidencePackItem, PaperSkeleton


class ScriptedFormulaLLM:
    def __init__(self, *, origin: str = "source_latex", ocr_status: str = "ocr_success") -> None:
        self.origin = origin
        self.ocr_status = ocr_status
        self.calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        text = "\n".join(message.content for message in messages)
        ref = _first_allowed_ref(text)
        return {
            "formula_cards": [
                {
                    "formula_id": "llm_overwrite_attempt",
                    "formula_origin": self.origin,
                    "formula_ocr_status": self.ocr_status,
                    "formula_explanation_status": "source_exact",
                    "purpose": "This formula defines the parser-derived objective.",
                    "symbols": [{"symbol": "L", "meaning": "loss"}],
                    "terms": [
                        {
                            "term": "regularization",
                            "meaning": "penalty term",
                            "encourages": "stable parameters",
                            "penalizes": "large weights",
                            "if_removed": "less regularization",
                        }
                    ],
                    "intuition": "The terms trade off fit and stability.",
                    "numeric_example": "INSUFFICIENT_EVIDENCE",
                    "what_if_removed": "INSUFFICIENT_EVIDENCE",
                    "weight_sensitivity": "INSUFFICIENT_EVIDENCE",
                    "plain_summary": "The formula summarizes an objective.",
                    "evidence_ref": ref,
                }
            ]
        }


class FailingFormulaLLM:
    calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        raise AssertionError("Unknown/raw formula evidence must not be sent for detailed LLM derivation")


def _first_allowed_ref(prompt: str) -> str:
    tail = prompt.split("Allowed evidence_ref values:", 1)[-1]
    for line in tail.splitlines():
        line = line.strip()
        if line.startswith("- "):
            value = line[2:].strip()
            if value and value != "NONE":
                return value
    raise AssertionError("No allowed evidence_ref in prompt")


def _skeleton() -> PaperSkeleton:
    return PaperSkeleton(
        paper_id="paper",
        title="Formula Provenance Paper",
        method_overview="The method uses an objective formula.",
    )


def _formula_item(*, origin: str = "", ocr_status: str = "") -> EvidencePackItem:
    return EvidencePackItem(
        claim_id="c_formula",
        claim_type="FORMULA_CONTEXT",
        evidence_ref="paper:eq001",
        passage_id="p_formula",
        passage_text="Formula: L = x + y. Context before: method objective. Context after: optimization step.",
        confidence=0.7,
        token_count=12,
        formula_origin=origin,
        formula_id="formula_001",
        formula_ocr_status=ocr_status,
    )


def _success_status() -> dict:
    return {
        "paper_id": "paper",
        "status": "SUCCESS",
        "allowed_for_user_display": True,
        "allowed_downstream": {"reading_display": True},
        "component_status": {
            "paper_card": "SUCCESS",
            "formula_cards": "SUCCESS",
            "teaching_cards": "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
        },
    }


def test_formula_card_v2_blocks_unknown_origin_without_llm_derivation() -> None:
    client = FailingFormulaLLM()
    pack = EvidencePack(paper_id="paper", items=[_formula_item()])

    bundle = asyncio.run(build_formula_cards_v2(pack, _skeleton(), client))

    assert client.calls == 0
    card = bundle.formula_cards[0]
    assert card.formula_origin == "unknown"
    assert card.formula_ocr_status == "not_available"
    assert card.coverage_status == "BLOCKED_RAW_ONLY"
    assert card.derivation_status == "blocked"
    assert card.confidence == 0.0
    assert card.symbols == []
    assert card.terms == []
    assert "INSUFFICIENT_EVIDENCE" in card.purpose

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=bundle.model_dump(mode="json"),
        understanding_status=_success_status(),
    ))
    assert not any(f.code == "FSA-5" for f in report.findings)


def test_formula_card_v2_preserves_evidence_origin_over_llm_output() -> None:
    client = ScriptedFormulaLLM(origin="source_latex", ocr_status="ocr_success")
    pack = EvidencePack(
        paper_id="paper",
        items=[_formula_item(origin="parser_latex", ocr_status="not_required")],
    )

    bundle = asyncio.run(build_formula_cards_v2(pack, _skeleton(), client))

    assert client.calls == 1
    card = bundle.formula_cards[0]
    assert card.formula_id == "formula_001"
    assert card.formula_origin == "parser_latex"
    assert card.formula_ocr_status == "not_required"
    assert card.formula_explanation_status == "parser_derived"
    assert card.purpose == "This formula defines the parser-derived objective."


def test_parser_latex_formula_with_evidence_ref_can_keep_detailed_explanation() -> None:
    client = ScriptedFormulaLLM(origin="parser_latex", ocr_status="not_required")
    pack = EvidencePack(
        paper_id="paper",
        items=[_formula_item(origin="parser_latex", ocr_status="not_required")],
    )

    bundle = asyncio.run(build_formula_cards_v2(pack, _skeleton(), client))
    card = bundle.formula_cards[0]

    assert card.formula_origin == "parser_latex"
    assert card.evidence_ref == "paper:eq001"
    assert card.symbols
    assert card.terms
    assert card.confidence > 0

    report = QualityAuditor().audit(ArtifactBundle(
        formula_cards=bundle.model_dump(mode="json"),
        claim_evidence={
            "paper_id": "paper",
            "claims": [{
                "claim_id": "c_formula",
                "claim_type": "FORMULA_CONTEXT",
                "evidence_ref": "paper:eq001",
                "passage_id": "p_formula",
                "formula_origin": "parser_latex",
            }],
        },
        understanding_status=_success_status(),
    ))
    assert not any(f.effect == "BLOCK" for f in report.findings)
