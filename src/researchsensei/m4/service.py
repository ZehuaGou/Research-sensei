from __future__ import annotations

import json
import re
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchsensei.llm.client import LLMClient, LLMClientError
from researchsensei.llm.types import ChatMessage, LLMConfig
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.m4 import (
    AdvisorEvaluation,
    AdvisorQuestion,
    FormulaSymbolExplanation,
    InteractiveAnswer,
    M4MemoryBundle,
    M4MemoryRecord,
    SelectionExplanation,
)


M4_MEMORY_FILENAME = "m4_memory.json"


class M4InteractionService:
    """Evidence-bound M4 interactions over existing M2 artifacts."""

    def __init__(
        self,
        *,
        job_id: str,
        run_dir: Path,
        artifacts: dict[str, object],
        llm_client: LLMClient | None = None,
    ) -> None:
        self.job_id = job_id
        self.run_dir = Path(run_dir)
        self.artifacts = artifacts
        self.llm_client = llm_client

    @property
    def memory_path(self) -> Path:
        return self.run_dir / M4_MEMORY_FILENAME

    def explain_selection(self, payload: dict[str, object]) -> SelectionExplanation:
        selected_text = _compact_user_text(payload.get("selected_text"), max_chars=2000)
        question = _compact_user_text(payload.get("user_question"), max_chars=1200)
        if not selected_text:
            return SelectionExplanation(
                status="DEGRADED",
                answer="没有收到选中的文本，M4 不能做基于证据的解释。",
                warnings=[_warning("MISSING_SELECTION", "解释选中文本需要 selected_text。")],
            )

        evidence = self._best_evidence(selected_text)
        warnings: list[WarningItem] = []
        status = "SUCCESS"
        confidence = evidence["score"]
        if not evidence.get("evidence_ref"):
            status = "DEGRADED"
            warnings.append(_warning("NO_TRACEABLE_EVIDENCE", "这段选中文本没有匹配到可追踪的 evidence_ref。"))
        elif confidence < 0.2:
            status = "DEGRADED"
            warnings.append(_warning("LOW_SELECTION_MATCH", "这段选中文本和证据片段的匹配度偏低。"))

        claim_text = str(evidence.get("claim_text") or evidence.get("text") or selected_text)
        section = str(evidence.get("section") or "当前论文")
        answer = (
            f"这段内容最接近论文中“{section}”部分的证据。"
            f"它支撑的局部论断是：{claim_text}"
        )
        if question:
            answer += f"\n\n结合你的追问，可以这样理解：{question}"

        result = SelectionExplanation(
            status=status,
            answer=answer,
            cited_evidence_refs=_list_of_one(evidence.get("evidence_ref")),
            cited_passage_ids=_list_of_one(evidence.get("passage_id")),
            relation_to_current_section=section,
            relation_to_paper_claim=claim_text,
            confidence=min(0.95, max(0.0, confidence)),
            warnings=warnings,
        )
        self._append_memory(
            memory_type="selection_explanation",
            text=selected_text,
            question=question,
            answer=result.answer,
            evidence_refs=result.cited_evidence_refs,
            confidence=result.confidence,
            source_artifact="claim_evidence",
            metadata={"status": result.status},
        )
        return result

    def explain_formula(self, payload: dict[str, object]) -> FormulaSymbolExplanation:
        formula_id = _clean(payload.get("formula_id"))
        symbol = _clean(payload.get("symbol") or payload.get("selected_symbol"))
        formula = self._find_formula(formula_id)
        if formula is None:
            return FormulaSymbolExplanation(
                status="DEGRADED",
                formula_id=formula_id,
                symbol=symbol,
                meaning="没有找到对应的公式卡片，暂时无法解释这个公式。",
                warnings=[_warning("FORMULA_NOT_FOUND", "formula_cards.json 中没有找到这个 formula_id。")],
            )

        evidence_ref = _clean(formula.get("evidence_ref"))
        matched_symbol = self._symbol_meaning(formula, symbol) if symbol else ("", "")
        full_explanation = _formula_full_explanation(formula)
        result = FormulaSymbolExplanation(
            status="SUCCESS" if evidence_ref else "DEGRADED",
            formula_id=_clean(formula.get("formula_id")) or formula_id,
            symbol=symbol or matched_symbol[0],
            meaning=matched_symbol[1] if symbol else full_explanation,
            source_sentence=_clean(formula.get("purpose")) or _clean(formula.get("plain_summary")),
            intuition=_clean(formula.get("intuition")) or _clean(formula.get("plain_summary")),
            numeric_example=_clean(formula.get("numeric_example")),
            role_in_method=_clean(formula.get("what_if_removed")) or _clean(formula.get("purpose")),
            evidence_ref=evidence_ref,
            formula_origin=_clean(formula.get("formula_origin")),
            formula_ocr_status=_clean(formula.get("formula_ocr_status")),
            formula_explanation_status=_clean(formula.get("formula_explanation_status"))
            or _clean(formula.get("derivation_status")),
            confidence=0.82 if evidence_ref else 0.35,
            warnings=[] if evidence_ref else [_warning("FORMULA_EVIDENCE_MISSING", "这张公式卡片没有 evidence_ref。")],
        )
        self._append_memory(
            memory_type="formula_explanation",
            text=result.meaning,
            question=symbol or formula_id,
            answer=result.meaning,
            evidence_refs=_list_of_one(result.evidence_ref),
            confidence=result.confidence,
            source_artifact="formula_cards",
            metadata={"formula_id": result.formula_id, "symbol": result.symbol},
        )
        return result

    def answer_question(self, payload: dict[str, object]) -> InteractiveAnswer:
        question = _compact_user_text(payload.get("question") or payload.get("user_question"), max_chars=1200)
        selected_text = _compact_user_text(payload.get("selected_text"), max_chars=2000)
        if not question and selected_text:
            question = f"请解释这段内容：{selected_text}"
        if not question:
            return InteractiveAnswer(
                status="DEGRADED",
                answer="还没有收到问题。",
                uncertainty="M4 需要一个问题，或者需要你先选中一段论文内容。",
                warnings=[_warning("QUESTION_MISSING", "缺少 question。")],
            )
        if not selected_text and _is_general_chat_question(question):
            return InteractiveAnswer(
                status="DEGRADED",
                answer=(
                    "我是 ResearchSensei 的 M4 论文助教，只基于当前论文证据回答问题。"
                    "你可以直接问：这篇论文解决什么问题、方法机制是什么、某个公式里的变量是什么意思，"
                    "或者选中论文内容后让我解释。"
                ),
                evidence_refs=[],
                memory_refs=[],
                uncertainty="这个问题没有指向当前论文证据，所以没有调用论文上下文或大模型。",
                follow_up_suggestions=[
                    "这篇论文解决了什么问题？",
                    "请解释核心方法机制。",
                    "某个公式里的变量分别是什么意思？",
                ],
                used_context={"memory": False, "artifacts": False, "llm": False},
                warnings=[_warning("M4_GENERAL_CHAT", "问题没有指向当前论文证据。")],
            )

        is_formula_question = _is_formula_question(question, selected_text)
        ignore_selection = _should_ignore_selection(question, selected_text)
        memory_hit = self._memory_hit(question=question, selected_text=selected_text)
        if (
            memory_hit is not None
            and not is_formula_question
            and not _looks_like_english_answer(memory_hit.answer)
            and not _is_low_quality_memory_answer(memory_hit)
            and not _is_too_thin_paper_level_memory_answer(memory_hit, question)
            and not _answer_exposes_internal_refs(memory_hit.answer)
            and not _memory_conflicts_with_paper_intent(memory_hit, question)
        ):
            return InteractiveAnswer(
                status="SUCCESS",
                answer=_strip_internal_refs_from_answer(_normalize_answer_text(memory_hit.answer, max_chars=1800)),
                evidence_refs=memory_hit.evidence_refs,
                memory_refs=[memory_hit.memory_id],
                uncertainty="这次回答来自 M4 记忆，并沿用当时记录的证据引用。",
                follow_up_suggestions=_follow_ups(),
                used_context={"memory": True, "artifacts": False, "llm": False},
            )

        formula = self._formula_from_text(question=question, selected_text=selected_text) if is_formula_question else None
        if formula is not None:
            answer, evidence_refs, confidence, warnings = self._answer_from_formula_card(formula)
        elif selected_text and not ignore_selection:
            selection = self.explain_selection({"selected_text": selected_text, "user_question": question})
            answer = selection.answer
            evidence_refs = selection.cited_evidence_refs
            warnings = selection.warnings
            confidence = selection.confidence
        else:
            answer, evidence_refs, confidence, warnings = self._answer_from_artifacts(question)

        used_context = {"memory": False, "artifacts": True, "llm": False}
        llm_result = self._answer_with_llm(
            question=question,
            selected_text=selected_text,
            fallback_answer=answer,
            allowed_evidence_refs=evidence_refs,
        )
        if llm_result is not None:
            answer = llm_result["answer"]
            evidence_refs = llm_result["evidence_refs"]
            used_context = {"memory": False, "artifacts": True, "llm": True}
            confidence = max(confidence, float(llm_result.get("confidence", 0.0)))
        elif self.llm_client is not None and evidence_refs:
            warnings = [
                *warnings,
                _warning("M4_LLM_FALLBACK", "大模型回答不可用或没有通过证据校验，已改用卡片证据回答。"),
            ]

        status = "SUCCESS" if evidence_refs else "DEGRADED"
        result = InteractiveAnswer(
            status=status,
            answer=answer,
            evidence_refs=evidence_refs,
            uncertainty=(
                "回答基于当前 M2 证据卡片。"
                if evidence_refs
                else "没有可追踪的 evidence_ref，所以只给出受限回答。"
            ),
            follow_up_suggestions=_follow_ups(),
            used_context=used_context,
            warnings=warnings,
        )
        self._append_memory(
            memory_type="interactive_answer",
            text=selected_text,
            question=question,
            answer=result.answer,
            evidence_refs=result.evidence_refs,
            confidence=confidence,
            source_artifact="paper_card",
            metadata={"selected_text": selected_text, "status": result.status},
        )
        return result

    def advisor_question(self, payload: dict[str, object]) -> AdvisorQuestion:
        mode = _clean(payload.get("advisor_mode")) or "group_meeting"
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        method = _claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea"))
        problem = _claim_text(paper_card.get("problem"))
        evidence_ref = _claim_ref(paper_card.get("method_overview")) or _claim_ref(paper_card.get("core_idea")) or self._first_evidence_ref()
        if not method:
            return AdvisorQuestion(
                status="DEGRADED",
                question="paper_card.method_overview 缺失，M4 暂时不能生成有证据支撑的组会追问。",
                warnings=[_warning("ADVISOR_EVIDENCE_MISSING", "paper_card 中缺少方法相关证据。")],
            )

        difficulty = "hard" if mode in {"defense", "qualifying_exam"} else "medium"
        question = (
            f"请解释：为什么论文的方法“{method}”能够合理回应它要解决的问题"
            f"{'：“' + problem + '”' if problem else ''}？"
        )
        result = AdvisorQuestion(
            question=question,
            target_concept=method,
            difficulty=difficulty,
            expected_answer_points=[point for point in [problem, method, "说明有 evidence_ref 支撑的方法机制"] if point],
            evidence_refs=_list_of_one(evidence_ref),
            question_type="method",
            follow_up_policy="deeper" if mode != "qualifying_exam" else "redirect_then_deeper",
            warnings=[] if evidence_ref else [_warning("ADVISOR_EVIDENCE_MISSING", "这个追问没有附带 evidence_ref。")],
        )
        self._append_memory(
            memory_type="advisor_question",
            text=result.target_concept,
            question=result.question,
            answer="",
            evidence_refs=result.evidence_refs,
            confidence=0.8 if result.evidence_refs else 0.35,
            source_artifact="paper_card",
            metadata={"advisor_mode": mode, "question_type": result.question_type},
        )
        return result

    def advisor_evaluate(self, payload: dict[str, object]) -> AdvisorEvaluation:
        answer = _clean(payload.get("user_answer") or payload.get("answer"))
        question = _clean(payload.get("question"))
        evidence_refs = _string_list(payload.get("evidence_refs")) or _list_of_one(self._first_evidence_ref())
        expected = _string_list(payload.get("expected_answer_points"))
        if not expected:
            expected = self._advisor_expected_points()

        answer_tokens = set(_tokens(answer))
        expected_tokens = set(_tokens(" ".join(expected)))
        overlap = len(answer_tokens & expected_tokens)
        score = min(1.0, max(0.0, (overlap / max(len(expected_tokens), 1)) * 1.4))
        if len(answer) > 80 and score < 0.55:
            score = 0.55
        missing = [point for point in expected if not (set(_tokens(point)) & answer_tokens)]
        misconceptions = [] if answer else ["还没有作答。"]
        feedback = (
            "不错，你已经碰到了有证据支撑的方法点。再补上问题背景、机制和证据引用，会更像组会里的完整回答。"
            if score >= 0.6
            else "这个回答还偏薄。建议把“论文要解决的问题、提出的机制、哪条证据支撑它”连成一条线。"
        )
        result = AdvisorEvaluation(
            score=round(score, 2),
            missing_points=missing[:4],
            misconceptions=misconceptions,
            next_question="你刚才描述的方法机制，对应哪一个 evidence_ref？",
            evidence_refs=evidence_refs,
            feedback=feedback,
            warnings=[] if evidence_refs else [_warning("EVALUATION_EVIDENCE_MISSING", "这次评价没有 evidence_refs。")],
        )
        self._append_memory(
            memory_type="advisor_evaluation",
            text=answer,
            question=question,
            answer=result.feedback,
            evidence_refs=evidence_refs,
            confidence=result.score,
            source_artifact="advisor_session",
            metadata={"score": result.score},
        )
        return result

    def get_memory(self) -> M4MemoryBundle:
        return self._read_memory()

    def clear_memory(self) -> M4MemoryBundle:
        bundle = M4MemoryBundle(job_id=self.job_id)
        self._write_memory(bundle)
        return bundle

    def _answer_with_llm(
        self,
        *,
        question: str,
        selected_text: str,
        fallback_answer: str,
        allowed_evidence_refs: list[str],
    ) -> dict[str, object] | None:
        if self.llm_client is None or not allowed_evidence_refs:
            return None
        allowed = set(allowed_evidence_refs)
        context = self._llm_context(allowed)
        if not context:
            return None
        prompt = {
            "job_id": self.job_id,
            "question": _compact_user_text(question, max_chars=700),
            "selected_text": _compact_user_text(selected_text, max_chars=700),
            "allowed_evidence_refs": allowed_evidence_refs,
            "fallback_answer": _normalize_answer_text(fallback_answer, max_chars=1200),
            "context": context,
            "output_rules": [
                "answer 必须是简体中文自然语言，即使 question、selected_text 或 context 是英文。",
                "不要逐字复述 selected_text；尤其不要整段复制 LaTeX、KaTeX 或公式源码。",
                "公式只保留必要符号，优先解释变量含义、机制和论文里的作用。",
                "回答要像真实助教：先直接回答问题，不要用“可以这样理解”“这段内容说明了”这类空泛开场。",
                "每个段落至少落到一个具体对象，例如变量、模块、训练项、数据集、指标、约束或论文中的方法步骤。",
                "解释公式时，如果 context 里有参数/符号或关键项，必须单独讲清楚它们各自的作用。",
                "论文级方法、贡献、证据问题开头必须用“重点：...”一句话凸显最核心抓手。",
                "随后用独立中文标签组织：问题：...；核心机制：...；为什么有效：...；对应证据：...。",
                "对应证据只写论文中的依据内容，不要写 evidence_ref、memory_ref、job id、b038、eq009、m4_xxx 等内部编号。",
                "优先使用 paper_card 和 claim_evidence 细节。",
                "不要只给一句概括；除非 context 不足，至少说明两个具体机制、数据集、指标或变量。",
                "最多 4 个短段落，每段不超过 160 个中文字符。",
            ],
            "required_json_schema": {
                "answer": "简体中文回答，只能使用 context 中的信息，不能整段复制公式源码",
                "evidence_refs": ["从 allowed_evidence_refs 中原样复制一个或多个引用"],
                "uncertainty": "中文说明：证据是否充分",
                "follow_up_suggestions": ["中文后续追问建议"],
            },
        }
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是 ResearchSensei 的 M4 论文助教。必须用简体中文回答，只能使用提供的 context。"
                    "即使用户问题、选中文本或证据是英文，也要翻译成中文解释。"
                    "不要整段复制 LaTeX/KaTeX/公式源码；要把公式转成中文含义和作用。"
                    "回答要像真实助教，先直接解释用户问的点，再展开变量、机制、证据中的具体细节。"
                    "论文级问题必须给正文细节，不要只回答标题、作者或一句摘要。"
                    "answer 字段面向用户，不能出现 evidence_ref、memory_ref、job id、b038、eq009、m4_xxx 等内部编号。"
                    "只返回 JSON，不要输出 Markdown。evidence_refs 必须从 allowed_evidence_refs 中原样复制。"
                    "如果 context 不足，就使用 fallback_answer，并保留相同的 evidence_refs。"
                ),
            ),
            ChatMessage(role="user", content=json.dumps(prompt, ensure_ascii=False)),
        ]
        try:
            data = _run_async_llm(
                self.llm_client.chat_json(
                    messages,
                    config=LLMConfig(
                        temperature=0.2,
                        max_tokens=2400,
                        json_mode=True,
                        timeout=90,
                        max_retries=1,
                        retry_delay=1.0,
                        disable_thinking=True,
                    ),
                )
            )
        except (LLMClientError, RuntimeError, ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        answer = _strip_internal_refs_from_answer(_normalize_answer_text(data.get("answer"), max_chars=1800))
        refs = _string_list(data.get("evidence_refs"))
        if not answer or not refs:
            return None
        if _looks_like_english_answer(answer):
            return None
        if _looks_like_thin_llm_answer(answer):
            return None
        if any(ref not in allowed for ref in refs):
            return None
        return {
            "answer": answer,
            "evidence_refs": _unique(refs),
            "confidence": 0.88,
        }

    def _answer_from_artifacts(self, question: str) -> tuple[str, list[str], float, list[WarningItem]]:
        lower = question.lower()
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        if any(term in lower for term in ["formula", "equation", "symbol", "公式", "方程", "符号"]):
            formula = self._find_formula("")
            if formula is not None:
                ref = _clean(formula.get("evidence_ref"))
                return (
                    f"最相关的公式卡片说明：{_clean(formula.get('purpose')) or _clean(formula.get('plain_summary'))}",
                    _list_of_one(ref),
                    0.78 if ref else 0.35,
                    [] if ref else [_warning("FORMULA_EVIDENCE_MISSING", "这张公式卡片没有 evidence_ref。")],
                )
        if _is_evidence_question(question):
            answer = _structured_paper_answer(paper_card, focus="对应证据")
            refs = _primary_paper_card_refs(paper_card)
            if answer and refs:
                return answer, refs, 0.82, []
        field_order = (
            ("实验结论", "experiment_summary", ["experiment", "result", "benchmark", "实验", "结果", "指标", "对比"]),
            ("局限", "limitations", ["limitation", "weakness", "future", "局限", "不足", "未来"]),
            ("方法", "method_overview", ["method", "mechanism", "how", "why", "方法", "机制", "怎么", "为什么"]),
            ("问题", "problem", ["problem", "task", "motivation", "问题", "任务", "动机"]),
            ("核心想法", "core_idea", ["idea", "contribution", "贡献", "核心", "想法"]),
        )
        for label, field, terms in field_order:
            if any(term in lower for term in terms):
                text = _claim_text(paper_card.get(field))
                ref = _claim_ref(paper_card.get(field))
                if text:
                    answer = _structured_paper_answer(paper_card, focus=label)
                    refs = _primary_paper_card_refs(paper_card) or _list_of_one(ref)
                    return answer or f"关于“{label}”：{text}", refs, 0.82 if refs else 0.4, []
        summary = _clean(paper_card.get("one_sentence_summary")) or _clean(paper_card.get("thirty_second"))
        refs = _primary_paper_card_refs(paper_card) or self._paper_card_refs()
        if summary:
            return _structured_paper_answer(paper_card, focus="论文核心") or f"论文层面的回答：{summary}", refs[:2], 0.75 if refs else 0.35, []
        return (
            "M4 没有找到足够的卡片或证据上下文来回答这个问题。",
            [],
            0.0,
            [_warning("M4_CONTEXT_MISSING", "没有可供用户使用的 M2 卡片产物。")],
        )

    def _formula_from_text(self, *, question: str, selected_text: str) -> dict[str, object] | None:
        text = f"{question} {selected_text}"
        normalized = _normalize(text)
        if not normalized:
            return None
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            return None
        for formula in formulas:
            if not isinstance(formula, dict):
                continue
            candidates = [
                _clean(formula.get("formula_id")),
                _clean(formula.get("formula_ref")),
                _clean(formula.get("evidence_ref")),
                _clean(formula.get("purpose")),
                _clean(formula.get("plain_summary")),
            ]
            for candidate in candidates:
                candidate_key = _normalize(candidate)
                if candidate_key and (candidate_key in normalized or normalized in candidate_key):
                    return formula
        return self._find_formula("")

    def _answer_from_formula_card(self, formula: dict[str, object]) -> tuple[str, list[str], float, list[WarningItem]]:
        evidence_ref = _clean(formula.get("evidence_ref"))
        warnings = [] if evidence_ref else [_warning("FORMULA_EVIDENCE_MISSING", "这张公式卡片没有 evidence_ref。")]
        return _formula_full_explanation(formula), _list_of_one(evidence_ref), 0.84 if evidence_ref else 0.35, warnings

    def _llm_context(self, allowed_refs: set[str]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        for field, claim in _paper_claims(paper_card):
            ref = _claim_ref(claim)
            text = _claim_text(claim)
            if ref in allowed_refs and text:
                rows.append({"source": f"paper_card.{field}", "evidence_ref": ref, "text": _compact_user_text(text, max_chars=900)})
        for candidate in self._evidence_candidates():
            ref = _clean(candidate.get("evidence_ref"))
            if ref not in allowed_refs:
                continue
            text = _clean(candidate.get("claim_text")) or _clean(candidate.get("quote_or_summary")) or _clean(candidate.get("text"))
            if text:
                rows.append({"source": "claim_evidence", "evidence_ref": ref, "text": _compact_user_text(text, max_chars=900)})
        for formula in _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", []):
            if not isinstance(formula, dict):
                continue
            ref = _clean(formula.get("evidence_ref"))
            if ref not in allowed_refs:
                continue
            text = _formula_context_text(formula)
            if text:
                rows.append({"source": "formula_cards", "evidence_ref": ref, "text": _compact_user_text(text, max_chars=900)})
        unique_rows: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            key = (row["source"], row["evidence_ref"])
            if key in seen:
                continue
            unique_rows.append(row)
            seen.add(key)
            if len(unique_rows) >= 8:
                break
        return unique_rows

    def _best_evidence(self, text: str) -> dict[str, object]:
        candidates = self._evidence_candidates()
        if not candidates:
            return {"score": 0.0}
        text_tokens = set(_tokens(text))
        best = candidates[0]
        best_score = -1.0
        normalized = _normalize(text)
        for candidate in candidates:
            haystack = " ".join(
                str(candidate.get(key) or "")
                for key in ("claim_text", "quote_or_summary", "source_sentence", "text", "section")
            )
            candidate_tokens = set(_tokens(haystack))
            score = len(text_tokens & candidate_tokens) / max(len(text_tokens), 1)
            if normalized and normalized in _normalize(haystack):
                score += 0.5
            if score > best_score:
                best = candidate
                best_score = score
        return {**best, "score": max(0.0, min(0.95, best_score))}

    def _evidence_candidates(self) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        passage_by_id: dict[str, dict[str, object]] = {}
        for passage in self._passages():
            passage_id = _clean(passage.get("passage_id"))
            if passage_id:
                passage_by_id[passage_id] = passage
            for ref in _string_list(passage.get("evidence_refs")):
                candidates.append({
                    "evidence_ref": ref,
                    "passage_id": passage_id,
                    "text": _clean(passage.get("text")) or _clean(passage.get("normalized_text")),
                    "section": _clean(passage.get("section")),
                })
        for claim in self._claims():
            passage_id = _clean(claim.get("passage_id"))
            passage = passage_by_id.get(passage_id, {})
            candidates.append({
                "evidence_ref": _clean(claim.get("evidence_ref")),
                "passage_id": passage_id,
                "claim_text": _clean(claim.get("claim_text")),
                "quote_or_summary": _clean(claim.get("quote_or_summary")),
                "source_sentence": _clean(claim.get("source_sentence")),
                "section": _clean(claim.get("section")) or _clean(passage.get("section")),
                "text": _clean(passage.get("text")) or _clean(passage.get("normalized_text")),
            })
        for field, claim in _paper_claims(_as_dict(self.artifacts.get("paper_card"))):
            ref = _claim_ref(claim)
            if ref:
                candidates.append({
                    "evidence_ref": ref,
                    "claim_text": _claim_text(claim),
                    "section": field,
                    "text": _claim_text(claim),
                })
        return [candidate for candidate in candidates if candidate.get("evidence_ref") or candidate.get("text")]

    def _find_formula(self, formula_id: str) -> dict[str, object] | None:
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            return None
        for formula in formulas:
            if not isinstance(formula, dict):
                continue
            if formula_id and _clean(formula.get("formula_id")) == formula_id:
                return formula
        for formula in formulas:
            if isinstance(formula, dict):
                return formula
        return None

    def _symbol_meaning(self, formula: dict[str, object], symbol: str) -> tuple[str, str]:
        symbols = formula.get("symbols", [])
        if isinstance(symbols, list):
            for item in symbols:
                if not isinstance(item, dict):
                    continue
                item_symbol = _clean(item.get("symbol"))
                if symbol and item_symbol == symbol:
                    return item_symbol, _clean(item.get("meaning")) or "这个符号的含义没有在公式卡片中说明。"
            for item in symbols:
                if isinstance(item, dict):
                    return _clean(item.get("symbol")), _clean(item.get("meaning")) or "这个符号的含义没有在公式卡片中说明。"
        return symbol, _clean(formula.get("plain_summary")) or _clean(formula.get("purpose")) or "这条公式在方法中的作用没有被说明。"

    def _paper_card_refs(self) -> list[str]:
        refs: list[str] = []
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        refs.extend(_string_list(paper_card.get("evidence_refs")))
        for _field, claim in _paper_claims(paper_card):
            ref = _claim_ref(claim)
            if ref:
                refs.append(ref)
        return _unique(refs)

    def _first_evidence_ref(self) -> str:
        refs = self._paper_card_refs()
        if refs:
            return refs[0]
        for candidate in self._evidence_candidates():
            ref = _clean(candidate.get("evidence_ref"))
            if ref:
                return ref
        return ""

    def _advisor_expected_points(self) -> list[str]:
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        return [
            point
            for point in [
                _claim_text(paper_card.get("problem")),
                _claim_text(paper_card.get("method_overview")),
                _claim_text(paper_card.get("core_idea")),
            ]
            if point
        ]

    def _claims(self) -> list[dict[str, object]]:
        claims = _as_dict(self.artifacts.get("claim_evidence")).get("claims", [])
        return [claim for claim in claims if isinstance(claim, dict)] if isinstance(claims, list) else []

    def _passages(self) -> list[dict[str, object]]:
        passages = _as_dict(self.artifacts.get("passage_index")).get("passages", [])
        return [passage for passage in passages if isinstance(passage, dict)] if isinstance(passages, list) else []

    def _memory_hit(self, *, question: str, selected_text: str) -> M4MemoryRecord | None:
        key = _normalize(question)
        selected_key = _normalize(selected_text)
        for record in reversed(self._read_memory().records):
            if record.memory_type != "interactive_answer":
                continue
            if _normalize(record.question) == key and _normalize(str(record.metadata.get("selected_text") or "")) == selected_key:
                return record
        return None

    def _append_memory(
        self,
        *,
        memory_type: str,
        text: str,
        question: str,
        answer: str,
        evidence_refs: list[str],
        confidence: float,
        source_artifact: str,
        metadata: dict[str, object] | None = None,
    ) -> M4MemoryRecord:
        bundle = self._read_memory()
        now = datetime.now(timezone.utc).isoformat()
        record = M4MemoryRecord(
            memory_id=f"m4_{uuid.uuid4().hex[:10]}",
            job_id=self.job_id,
            memory_type=memory_type,
            text=_compact_user_text(text, max_chars=4000),
            question=_compact_user_text(question, max_chars=1000),
            answer=_normalize_answer_text(answer, max_chars=4000),
            source_artifact=source_artifact,
            evidence_refs=_unique(evidence_refs),
            confidence=round(max(0.0, min(1.0, confidence)), 2),
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        bundle.records.append(record)
        self._write_memory(bundle)
        return record

    def _read_memory(self) -> M4MemoryBundle:
        if not self.memory_path.exists():
            return M4MemoryBundle(job_id=self.job_id)
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            return M4MemoryBundle.model_validate(data)
        except Exception:
            return M4MemoryBundle(
                job_id=self.job_id,
                records=[],
            )

    def _write_memory(self, bundle: M4MemoryBundle) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(
            json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _paper_claims(paper_card: dict[str, object]) -> list[tuple[str, object]]:
    fields = ["problem", "core_idea", "method_overview", "experiment_summary", "limitations", "background", "bottleneck"]
    return [(field, paper_card.get(field)) for field in fields if paper_card.get(field)]


def _run_async_llm(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if hasattr(coro, "close"):
        coro.close()
    raise RuntimeError("M4InteractionService cannot run async LLM calls inside an active event loop.")


def _claim_text(value: object) -> str:
    if isinstance(value, dict):
        return _clean(value.get("text") or value.get("plain"))
    return _clean(value)


def _claim_ref(value: object) -> str:
    if isinstance(value, dict):
        return _clean(value.get("evidence_ref"))
    return ""


def _paper_card_claim_rows(paper_card: dict[str, object]) -> list[tuple[str, str, str]]:
    labels = {
        "problem": "研究问题",
        "core_idea": "核心想法",
        "method_overview": "方法机制",
        "experiment_summary": "实验结论",
        "limitations": "局限",
    }
    rows: list[tuple[str, str, str]] = []
    for field in ["problem", "core_idea", "method_overview", "experiment_summary", "limitations"]:
        text = _claim_text(paper_card.get(field))
        ref = _claim_ref(paper_card.get(field))
        if text and ref:
            rows.append((labels[field], text, ref))
    return rows


def _primary_paper_card_refs(paper_card: dict[str, object]) -> list[str]:
    return _unique([ref for _label, _text, ref in _paper_card_claim_rows(paper_card)])


def _paper_card_evidence_answer(paper_card: dict[str, object]) -> str:
    rows = _paper_card_claim_rows(paper_card)
    if not rows:
        return ""
    rendered = [f"{label}：{text}" for label, text, _ref in rows]
    return "当前论文卡片中的主要依据可以这样看：" + "；".join(rendered) + "。"


def _structured_paper_answer(paper_card: dict[str, object], *, focus: str = "") -> str:
    rows = _paper_card_claim_rows(paper_card)
    if not rows:
        summary = _clean(paper_card.get("one_sentence_summary")) or _clean(paper_card.get("thirty_second"))
        return f"重点：{summary}" if summary else ""
    by_label = {label: text for label, text, _ref in rows}
    problem = by_label.get("研究问题", "")
    idea = by_label.get("核心想法", "")
    method = by_label.get("方法机制", "")
    experiment = by_label.get("实验结论", "")
    limitations = by_label.get("局限", "")
    summary = _clean(paper_card.get("one_sentence_summary")) or _clean(paper_card.get("thirty_second"))

    focus_text = method or idea or summary or problem
    if focus == "实验结论" and experiment:
        focus_text = experiment
    elif focus == "研究问题" and problem:
        focus_text = problem
    elif focus == "核心想法" and idea:
        focus_text = idea

    parts = [f"重点：{focus_text}"]
    if problem:
        parts.append(f"问题：{problem}")
    if idea or method:
        mechanism = "；".join(item for item in [idea, method] if item)
        parts.append(f"核心机制：{mechanism}")
    why_items = []
    if method:
        why_items.append("它把论文的方法主张落到可执行的建模步骤上")
    if experiment:
        why_items.append(f"实验结论显示：{experiment}")
    if limitations:
        why_items.append(f"同时要注意局限：{limitations}")
    if why_items:
        parts.append(f"为什么有效：{'；'.join(why_items)}")
    evidence_lines = [f"{label}来自论文卡片中的正文依据：{text}" for label, text, _ref in rows[:4]]
    if evidence_lines:
        parts.append("对应证据：" + "；".join(evidence_lines))
    return "\n\n".join(parts)


def _formula_context_text(formula: dict[str, object]) -> str:
    purpose = _clean(formula.get("purpose")) or _clean(formula.get("plain_summary"))
    intuition = _clean(formula.get("intuition"))
    example = _clean(formula.get("numeric_example"))
    removed = _clean(formula.get("what_if_removed")) or _clean(formula.get("remove_effect"))
    sensitivity = _clean(formula.get("weight_sensitivity")) or _clean(formula.get("weight_change_effect"))
    parts = [
        item
        for item in [
            f"目标：{purpose}" if purpose else "",
            f"参数/符号：{_formula_symbol_summary(formula)}" if _formula_symbol_summary(formula) else "",
            f"关键项：{_formula_term_summary(formula)}" if _formula_term_summary(formula) else "",
            f"直觉：{intuition}" if intuition else "",
            f"例子：{example}" if example else "",
            f"拿掉影响：{removed}" if removed else "",
            f"权重变化：{sensitivity}" if sensitivity else "",
        ]
        if item
    ]
    return "；".join(parts) or _clean(formula.get("formula_raw"))


def _formula_full_explanation(formula: dict[str, object]) -> str:
    purpose = _clean(formula.get("purpose")) or _clean(formula.get("plain_summary")) or "这条公式用于说明论文方法中的一个计算步骤。"
    symbols = _formula_symbol_summary(formula)
    terms = _formula_term_summary(formula)
    intuition = _clean(formula.get("intuition")) or _clean(formula.get("plain_summary"))
    example = _clean(formula.get("numeric_example"))
    removed = _clean(formula.get("what_if_removed")) or _clean(formula.get("remove_effect"))
    sensitivity = _clean(formula.get("weight_sensitivity")) or _clean(formula.get("weight_change_effect"))

    parts = [f"先看目标：{purpose}"]
    if symbols:
        parts.append(f"参数/符号：{symbols}")
    if terms:
        parts.append(f"关键项：{terms}")
    if intuition and intuition != purpose:
        parts.append(f"直觉：{intuition}")
    if example:
        parts.append(f"例子：{example}")
    if removed:
        parts.append(f"拿掉影响：{removed}")
    if sensitivity:
        parts.append(f"权重变化：{sensitivity}")
    return "\n\n".join(parts)


def _formula_symbol_summary(formula: dict[str, object]) -> str:
    rows = formula.get("symbols", [])
    if not isinstance(rows, list):
        return ""
    rendered: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        symbol = _clean(item.get("symbol"))
        meaning = _clean(item.get("meaning"))
        if symbol and meaning:
            rendered.append(f"{symbol} 表示 {meaning}")
        elif meaning:
            rendered.append(meaning)
        if len(rendered) >= 8:
            break
    return "；".join(rendered)


def _formula_term_summary(formula: dict[str, object]) -> str:
    rows = formula.get("terms", [])
    if not isinstance(rows, list):
        return ""
    rendered: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        term = _clean(item.get("term"))
        details = [
            _clean(item.get("meaning")),
            f"鼓励 {_clean(item.get('encourages'))}" if _clean(item.get("encourages")) else "",
            f"惩罚 {_clean(item.get('penalizes'))}" if _clean(item.get("penalizes")) else "",
            f"去掉后 {_clean(item.get('if_removed'))}" if _clean(item.get("if_removed")) else "",
        ]
        detail_text = "，".join(detail for detail in details if detail)
        if term and detail_text:
            rendered.append(f"{term}：{detail_text}")
        elif detail_text:
            rendered.append(detail_text)
        if len(rendered) >= 8:
            break
    return "；".join(rendered)


def _warning(code: str, message: str) -> WarningItem:
    return WarningItem(code=code, message=message)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _compact_user_text(value: object, *, max_chars: int) -> str:
    text = _clean(value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:，。；：、）\]\}])", r"\1", text)
    text = re.sub(r"([（\[\{])\s+", r"\1", text).strip()
    if len(text) > max_chars:
        return f"{text[:max_chars].rstrip()}..."
    return text


def _normalize_answer_text(value: object, *, max_chars: int) -> str:
    text = _clean(value).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"([A-Za-z])\n(?=[A-Za-z])", r"\1 ", text).strip()
    if len(text) > max_chars:
        return f"{text[:max_chars].rstrip()}..."
    return text


def _answer_exposes_internal_refs(value: str) -> bool:
    return bool(
        re.search(r"(?i)(?:evidence_ref|memory_ref|m4_[a-z0-9_]+|(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,})", value)
    )


def _strip_internal_refs_from_answer(value: str) -> str:
    text = value
    text = re.sub(
        r"（\s*证据[:：]?\s*(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,}(?:[、,，]\s*(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,})*\s*）",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\n?\s*证据[:：]\s*(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,}(?:[、,，]\s*(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,})*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\n?\s*记忆[:：]\s*m4_[A-Za-z0-9_]+(?:[、,，]\s*m4_[A-Za-z0-9_]+)*", "", text)
    text = re.sub(r"(?i)(?:evidence_ref|memory_ref)", "内部依据", text)
    text = re.sub(r"(?i)(?:[A-Za-z0-9_-]+:)?(?:b|eq)\d{2,}", "", text)
    text = re.sub(r"m4_[A-Za-z0-9_]+", "", text)
    text = re.sub(r"（\s*）", "", text)
    text = re.sub(r"\s+([,.;:，。；：、）\]\}])", r"\1", text)
    text = re.sub(r"([（\[\{])\s+", r"\1", text)
    text = re.sub(r"[、,，]\s*([）。；;])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _looks_like_english_answer(value: str) -> bool:
    text = re.sub(r"`[^`]*`", "", value)
    latin_letters = len(re.findall(r"[A-Za-z]", text))
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    if latin_letters < 32:
        return False
    if chinese_chars == 0:
        return True
    if chinese_chars < 20:
        return latin_letters > 60
    return latin_letters > max(220, chinese_chars * 5)


def _looks_like_thin_llm_answer(value: str) -> bool:
    text = _clean(value)
    thin_markers = [
        "仅包含论文标题",
        "只包含论文标题",
        "标题和作者",
        "无法进一步阐述",
        "无法展开",
        "没有提供上下文",
        "没有足够上下文",
    ]
    return any(marker in text for marker in thin_markers)


def _is_general_chat_question(question: str) -> bool:
    text = re.sub(r"[\s，。！？,.!?]+", "", question.lower())
    if not text:
        return False
    exact_questions = {
        "你好",
        "您好",
        "hi",
        "hello",
        "你好吗",
        "在吗",
        "讲个笑话",
        "说个笑话",
        "你能做什么",
        "你是谁",
        "你现在是谁",
        "你是什么",
        "m4是谁",
        "助教是谁",
    }
    if text in exact_questions:
        return True
    return (
        len(text) <= 14
        and any(marker in text for marker in ["你是谁", "你好吗", "讲笑话", "闲聊", "聊天"])
    )


def _is_evidence_question(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ["证据", "evidence", "对应哪", "引用"])


def _is_paper_level_question(question: str) -> bool:
    text = question.lower()
    return any(
        term in text
        for term in [
            "这篇论文",
            "整篇",
            "核心方法",
            "核心贡献",
            "核心想法",
            "主要方法",
            "讲清楚",
            "讲透",
            "summary",
            "method",
            "contribution",
        ]
    )


def _should_ignore_selection(question: str, selected_text: str) -> bool:
    if not selected_text:
        return False
    selected = selected_text.strip()
    selected_markers = [
        "用中文讲透这篇论文",
        "像组会一样追问这篇论文",
        "请用中文讲清楚这篇论文",
    ]
    if any(selected.startswith(marker) for marker in selected_markers):
        return True
    return _is_paper_level_question(question) or _is_evidence_question(question)


def _is_low_quality_memory_answer(record: M4MemoryRecord) -> bool:
    text = f"{record.answer} {record.question} {record.text}"
    bad_markers = [
        "booktabs",
        "multirow",
        "LaTeX 宏包",
        "论文标题和作者信息",
        "标题和作者信息",
        "现有证据仅包含论文标题",
        "full_text",
        "作者信息",
    ]
    return any(marker in text for marker in bad_markers)


def _is_too_thin_paper_level_memory_answer(record: M4MemoryRecord, question: str) -> bool:
    if not _is_paper_level_question(question):
        return False
    answer = _clean(record.answer)
    if len(answer) < 120:
        return True
    detail_markers = ["首先", "然后", "因此", "实验", "数据集", "指标", "证据", "b0", "eq"]
    sentence_count = answer.count("。") + answer.count("\n")
    return sentence_count < 2 and not any(marker in answer for marker in detail_markers)


def _memory_conflicts_with_paper_intent(record: M4MemoryRecord, question: str) -> bool:
    if not (_is_paper_level_question(question) or _is_evidence_question(question)):
        return False
    text = f"{record.answer} {record.question}"
    if any(marker in text for marker in ["标题", "作者", "宏包", "full_text", "booktabs"]):
        return True
    return False


def _is_formula_question(question: str, selected_text: str) -> bool:
    text = f"{question} {selected_text}".lower()
    return any(term in text for term in ["formula", "equation", "symbol", "公式", "方程", "符号"])


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [_clean(item) for item in value if _clean(item)]
    if isinstance(value, tuple):
        return [_clean(item) for item in value if _clean(item)]
    text = _clean(value)
    return [text] if text else []


def _list_of_one(value: object) -> list[str]:
    text = _clean(value)
    return [text] if text else []


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _normalize(value: str) -> str:
    return " ".join(_tokens(value))


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", value) if len(token) > 1]


def _follow_ups() -> list[str]:
    return [
        "这句话对应论文里的哪条依据？",
        "能用一句话讲清楚这个方法吗？",
        "这个结果之后还剩下什么局限？",
    ]
