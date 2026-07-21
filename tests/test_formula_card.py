from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.formula_card import build_formula_cards
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


class BatchFormulaLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.batch_sizes: list[int] = []
        self.configs = []

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        self.configs.append(config)
        text = "\n".join(message.content for message in messages)
        refs = _allowed_refs(text)
        self.batch_sizes.append(len(refs))
        return {
            "formula_cards": [
                {
                    "formula_id": f"llm_{index}",
                    "formula_origin": "parser_latex",
                    "formula_ocr_status": "not_required",
                    "formula_explanation_status": "parser_derived",
                    "purpose": f"Formula {index} defines one part of the objective.",
                    "symbols": [{"symbol": f"x_{index}", "meaning": "state variable"}],
                    "terms": [
                        {
                            "term": f"term_{index}",
                            "meaning": "objective component",
                            "encourages": "stable optimization",
                            "penalizes": "unstable assignments",
                            "if_removed": "the objective loses one constraint",
                        }
                    ],
                    "intuition": "Each term explains one formula slot.",
                    "numeric_example": "INSUFFICIENT_EVIDENCE",
                    "what_if_removed": "INSUFFICIENT_EVIDENCE",
                    "weight_sensitivity": "INSUFFICIENT_EVIDENCE",
                    "plain_summary": "The formula is explained from its evidence.",
                    "evidence_ref": ref,
                }
                for index, ref in enumerate(refs, start=1)
            ]
        }


class AnthropicBatchFormulaLLM(BatchFormulaLLM):
    provider = SimpleNamespace(kind="anthropic_compatible", name="cc_switch")


class SplitRetryFormulaLLM(BatchFormulaLLM):
    async def chat_json(self, messages, *, config=None):
        refs = _allowed_refs("\n".join(message.content for message in messages))
        self.calls += 1
        self.batch_sizes.append(len(refs))
        if len(refs) > 1:
            raise ValueError("simulated truncated JSON")
        return {
            "formula_cards": [
                {
                    "formula_id": f"llm_{refs[0]}",
                    "formula_origin": "parser_latex",
                    "formula_ocr_status": "not_required",
                    "formula_explanation_status": "parser_derived",
                    "purpose": "Formula defines one recoverable single-item card.",
                    "symbols": [{"symbol": "x", "meaning": "state variable"}],
                    "terms": [
                        {
                            "term": "term",
                            "meaning": "objective component",
                            "encourages": "stable optimization",
                            "penalizes": "unstable assignments",
                            "if_removed": "the objective loses one constraint",
                        }
                    ],
                    "intuition": "Single formula retry works.",
                    "numeric_example": "INSUFFICIENT_EVIDENCE",
                    "what_if_removed": "INSUFFICIENT_EVIDENCE",
                    "weight_sensitivity": "INSUFFICIENT_EVIDENCE",
                    "plain_summary": "Recovered from split retry.",
                    "evidence_ref": refs[0],
                }
            ]
        }


class FailingFormulaLLM:
    calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        raise AssertionError("Unknown/raw formula evidence must not be sent for detailed LLM derivation")


class EmptyFormulaLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        return {"formula_cards": []}


class CompactRetryFormulaLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.prompts: list[str] = []

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        text = "\n".join(message.content for message in messages)
        self.prompts.append(text)
        if self.calls == 1:
            raise ValueError("LLM returned empty content (stop_reason=max_tokens; content_block_types=thinking)")
        ref = _first_allowed_ref(text)
        return {
            "formula_cards": [
                {
                    "formula_id": "retry_formula",
                    "formula_origin": "source_latex",
                    "formula_ocr_status": "not_required",
                    "formula_explanation_status": "source_exact",
                    "purpose": "Recovered compact retry explanation.",
                    "symbols": [{"symbol": "x", "meaning": "input point"}],
                    "terms": [],
                    "intuition": "Recovered by shorter JSON prompt.",
                    "numeric_example": "INSUFFICIENT_EVIDENCE",
                    "what_if_removed": "INSUFFICIENT_EVIDENCE",
                    "weight_sensitivity": "INSUFFICIENT_EVIDENCE",
                    "plain_summary": "Recovered card.",
                    "evidence_ref": ref,
                }
            ]
        }


def _allowed_refs(prompt: str) -> list[str]:
    refs: list[str] = []
    for line in prompt.splitlines():
        line = line.strip()
        if line.startswith("- evidence_ref:"):
            value = line.split(":", 1)[1].strip()
            if value:
                refs.append(value)
    if refs:
        return refs
    return [_first_allowed_ref(prompt)]


def _first_allowed_ref(prompt: str) -> str:
    for line in prompt.splitlines():
        line = line.strip()
        if line.startswith("- evidence_ref:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    separators = [
        "Allowed evidence_ref values:",
        "允许的 evidence_ref：",
        "允许的 evidence_ref:",
    ]
    for separator in separators:
        if separator not in prompt:
            continue
        tail = prompt.split(separator, 1)[-1]
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


def _formula_item(
    *,
    origin: str = "",
    ocr_status: str = "",
    evidence_ref: str = "paper:eq001",
    formula_id: str = "formula_001",
) -> EvidencePackItem:
    return EvidencePackItem(
        claim_id=f"c_{formula_id}",
        claim_type="FORMULA_CONTEXT",
        evidence_ref=evidence_ref,
        passage_id=f"p_{formula_id}",
        passage_text="Formula: L = x + y. Context before: method objective. Context after: optimization step.",
        confidence=0.7,
        token_count=12,
        formula_origin=origin,
        formula_id=formula_id,
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


def test_formula_card_blocks_unknown_origin_without_llm_derivation() -> None:
    client = FailingFormulaLLM()
    pack = EvidencePack(paper_id="paper", items=[_formula_item()])

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

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


def test_source_latex_missing_llm_card_keeps_explicit_failure_card_without_structure_fallback() -> None:
    client = EmptyFormulaLLM()
    pack = EvidencePack(
        paper_id="paper",
        items=[
            EvidencePackItem(
                claim_id="c_threshold",
                claim_type="FORMULA_CONTEXT",
                evidence_ref="paper:eq_threshold",
                passage_id="p_threshold",
                passage_text=(
                    "O(x_i) = \\begin{cases} "
                    "1, &\\text{if $\\frac{S(x_i) - \\overline{S(x_i)}}{\\overline{S(x_i)}} > \\tau $,} \\\\ "
                    "0, &\\text{otherwise,} \\end{cases}"
                ),
                confidence=0.7,
                token_count=28,
                formula_origin="source_latex",
                formula_id="source_latex_formula_threshold",
                formula_ocr_status="not_required",
            )
        ],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert client.calls == 1
    card = bundle.formula_cards[0]
    assert card.evidence_ref == "paper:eq_threshold"
    assert card.coverage_status == "LLM_FAILED"
    assert card.derivation_status == "llm_failed"
    assert card.confidence == 0.0
    assert card.symbols == []
    assert card.terms == []
    assert "LLM 没有返回" in card.purpose
    assert any("NO_FORMULA_CARDS_FROM_LLM" in warning for warning in bundle.warnings)
    assert not any("STRUCTURE_DERIVED" in warning for warning in bundle.warnings)


def test_single_formula_thinking_only_failure_gets_compact_llm_retry() -> None:
    client = CompactRetryFormulaLLM()
    pack = EvidencePack(
        paper_id="paper",
        items=[
            _formula_item(
                origin="source_latex",
                ocr_status="not_required",
                evidence_ref="paper:eq_retry",
                formula_id="source_latex_formula_retry",
            )
        ],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert client.calls == 2
    assert "上一次请求没有给出最终 JSON" in client.prompts[1]
    card = bundle.formula_cards[0]
    assert card.coverage_status == "LLM_EXPLAINED"
    assert card.evidence_ref == "paper:eq_retry"
    assert any("FORMULA_LLM_COMPACT_RETRY" in warning for warning in bundle.warnings)
    assert not any("LLM_CARD_MISSING_FOR_FORMULA" in warning for warning in bundle.warnings)


def test_attention_run_formulas_missing_llm_cards_are_explicit_failures_without_structure_fallbacks() -> None:
    client = EmptyFormulaLLM()
    formulae = [
        "\\begin{split} \\mathrm{Attention}&=\\mathrm{Concat}(\\mathbf{A}^{(1)}, \\mathbf{A}^{(2)}) \\\\ \\mathbf{A}^{(1)}&=\\mathrm{MultiHead}(\\mathbf{X}^{(1)}) \\\\ \\mathbf{A}^{(2)}&=\\mathrm{Global}(\\mathbf{X}^{(2)}) \\end{split}",
        "\\mathrm{Attention}(\\mathbf{Q}, \\mathbf{K}, \\mathbf{V})=\\mathrm{Softmax}(\\frac{\\mathbf{Q}\\mathbf{K}^{T}}{\\sqrt{d_{k}}})\\mathbf{V}",
        "\\mathrm{Attention}(\\mathbf{S}, \\mathbf{V})=\\mathrm{Softmax}(\\mathbf{S})\\mathbf{V}",
        "\\textit{head}_{i}=\\mathrm{Attention}(\\mathbf{Q}W_{i}^{Q}, \\mathbf{K}W_{i}^{K}, \\mathbf{V}W_{i}^{V})",
        "\\mathrm{MultiHead}(\\mathbf{Q}, \\mathbf{K}, \\mathbf{V})=\\mathrm{Concat}(\\textit{head}_{1}, \\cdots, \\textit{head}_{h})W^{O}",
        "\\mathrm{F1} = 2\\times \\frac{\\mathrm{Precision}\\times \\mathrm{Recall}}{\\mathrm{Precision}+\\mathrm{Recall}}",
        "z^{i, j} = \\argmax_{c\\in \\{0, 1\\}}(\\log \\pi^{i, j}_{c} + g^{i, j}_{c})",
        "z^{i, j}_{c} = \\frac{\\exp((\\log \\pi^{i, j}_{c} + g^{i, j}_{c})/\\tau)}{\\sum\\limits_{v\\in \\{0, 1\\}}\\exp((\\log \\pi^{i, j}_{v} + g^{i, j}_{v})/\\tau)}",
        "\\mathcal{L}_{mse} = \\frac{1}{M}\\sum\\limits_{t=1}^{n}\\vert\\vert\\mathcal{Y}^{(t)} - \\hat{\\mathcal{Y}}^{(t)}\\vert\\vert^{2}_{2}",
        "\\mathrm{Precision} = \\frac{\\mathrm{TP}}{\\mathrm{TP}+\\mathrm{FP}}",
        "\\mathrm{Recall} = \\frac{\\mathrm{TP}}{\\mathrm{TP}+\\mathrm{FN}}",
        "\\mathbf{x}^{\\prime}_{i} = \\sum\\limits_{j\\in \\mathcal{N}(i)}h_{\\mathbf{\\Theta}}(\\mathbf{x}_{i}\\vert\\vert \\mathbf{x}_{j}-\\mathbf{x}_{j}\\vert\\vert \\mathbf{x}_{j}+\\mathbf{x}_{i})",
        "\\mathcal{L}_{s} = \\sum\\limits_{1\\leq i,j \\leq M, i\\neq j} \\log \\pi^{i, j}_{1}",
        "\\hat{\\mathbf{y}}^{(t)} = \\sum\\limits_{i=1}^{M}\\vert\\vert\\mathcal{Y}_{i}^{(t)} - \\hat{\\mathcal{Y}}_{i}^{(t)}\\vert\\vert^{2}_{2}",
        "\\tilde{x} = \\frac{x-\\min X_{train}}{\\max X_{train} - \\min X_{train}}",
    ]
    pack = EvidencePack(
        paper_id="paper",
        items=[
            EvidencePackItem(
                claim_id=f"c_formula_{index}",
                claim_type="FORMULA_CONTEXT",
                evidence_ref=f"paper:eq{index:03d}",
                passage_id=f"p_formula_{index}",
                passage_text=formula,
                confidence=0.7,
                token_count=30,
                formula_origin="source_latex",
                formula_id=f"source_latex_formula_{index:03d}",
                formula_ocr_status="not_required",
            )
            for index, formula in enumerate(formulae, start=1)
        ],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert len(bundle.formula_cards) == 15
    assert {card.evidence_ref for card in bundle.formula_cards} == {
        f"paper:eq{index:03d}" for index in range(1, 16)
    }
    assert all(card.coverage_status == "LLM_FAILED" for card in bundle.formula_cards)
    assert any("NO_FORMULA_CARDS_FROM_LLM" in warning for warning in bundle.warnings)
    assert any("FORMULA_LLM_BATCH_SPLIT_RETRY" in warning for warning in bundle.warnings)
    assert not any("STRUCTURE_DERIVED" in warning for warning in bundle.warnings)


def test_formula_card_preserves_evidence_origin_over_llm_output() -> None:
    client = ScriptedFormulaLLM(origin="source_latex", ocr_status="ocr_success")
    pack = EvidencePack(
        paper_id="paper",
        items=[_formula_item(origin="parser_latex", ocr_status="not_required")],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert client.calls == 1
    card = bundle.formula_cards[0]
    assert card.formula_id == "formula_001"
    assert card.formula_origin == "parser_latex"
    assert card.formula_ocr_status == "not_required"
    assert card.formula_explanation_status == "parser_derived"
    assert card.purpose == "This formula defines the parser-derived objective."


def test_formula_cards_batch_ten_derivable_formulas_in_one_llm_call() -> None:
    client = BatchFormulaLLM()
    pack = EvidencePack(
        paper_id="paper",
        items=[
            _formula_item(
                origin="parser_latex",
                ocr_status="not_required",
                evidence_ref=f"paper:eq{i:03d}",
                formula_id=f"formula_{i:03d}",
            )
            for i in range(1, 11)
        ],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert client.calls == 1
    assert client.batch_sizes == [10]
    assert len(bundle.formula_cards) == 10
    assert {card.evidence_ref for card in bundle.formula_cards} == {
        f"paper:eq{i:03d}" for i in range(1, 11)
    }
    assert not any("LLM_CARD_MISSING_FOR_FORMULA" in warning for warning in bundle.warnings)


def test_anthropic_compatible_formula_cards_use_bounded_reasoning_batches(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHSENSEI_FORMULA_CARD_BATCH_SIZE", raising=False)
    monkeypatch.delenv("RESEARCHSENSEI_FORMULA_CARD_CONCURRENCY", raising=False)
    client = AnthropicBatchFormulaLLM()
    pack = EvidencePack(
        paper_id="paper",
        items=[
            _formula_item(
                origin="parser_latex",
                ocr_status="not_required",
                evidence_ref=f"paper:eq{i:03d}",
                formula_id=f"formula_{i:03d}",
            )
            for i in range(1, 8)
        ],
    )

    progress: list[tuple[int, int]] = []
    bundle = asyncio.run(
        build_formula_cards(
            pack,
            _skeleton(),
            client,
            progress=lambda completed, total: progress.append((completed, total)),
        )
    )

    assert client.calls == 3
    assert client.batch_sizes == [3, 3, 1]
    assert all(config.max_tokens == 12_000 for config in client.configs)
    assert all(config.disable_thinking is True for config in client.configs)
    assert len(bundle.formula_cards) == 7
    assert progress == [(0, 3), (1, 3), (2, 3), (3, 3)]
    assert not any("LLM_CARD_MISSING_FOR_FORMULA" in warning for warning in bundle.warnings)


def test_failed_formula_batch_splits_to_single_formula_retries(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_FORMULA_CARD_BATCH_SIZE", "10")
    client = SplitRetryFormulaLLM()
    pack = EvidencePack(
        paper_id="paper",
        items=[
            _formula_item(
                origin="parser_latex",
                ocr_status="not_required",
                evidence_ref=f"paper:eq{i:03d}",
                formula_id=f"formula_{i:03d}",
            )
            for i in range(1, 4)
        ],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))

    assert client.batch_sizes == [3, 1, 1, 1]
    assert len(bundle.formula_cards) == 3
    assert all(card.coverage_status == "LLM_EXPLAINED" for card in bundle.formula_cards)
    assert any("FORMULA_LLM_BATCH_SPLIT_RETRY" in warning for warning in bundle.warnings)
    assert not any("LLM_CARD_MISSING_FOR_FORMULA" in warning for warning in bundle.warnings)


def test_parser_latex_formula_with_evidence_ref_can_keep_detailed_explanation() -> None:
    client = ScriptedFormulaLLM(origin="parser_latex", ocr_status="not_required")
    pack = EvidencePack(
        paper_id="paper",
        items=[_formula_item(origin="parser_latex", ocr_status="not_required")],
    )

    bundle = asyncio.run(build_formula_cards(pack, _skeleton(), client))
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
