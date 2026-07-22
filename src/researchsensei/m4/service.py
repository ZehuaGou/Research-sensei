from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from researchsensei.llm.client import LLMClient, LLMClientError
from researchsensei.llm.types import ChatMessage, LLMConfig
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.m4 import (
    AdvisorEvaluation,
    AdvisorQuestion,
    FormulaSymbolExplanation,
    GroundedClaim,
    InteractiveAnswer,
    M4ContextTrace,
    M4MemoryBundle,
    M4MemoryRecord,
    SelectionExplanation,
)


M4_MEMORY_FILENAME = "m4_memory.json"
M4_MEMORY_SCHEMA_VERSION = "m4_memory.v2"
M4_MEMORY_MAX_RECORDS = 200
M4_MEMORY_MAX_BYTES = 1_048_576
M4_MEMORY_MAX_WARNINGS = 16
M4_LLM_TIMEOUT_SECONDS = 80.0
M4_LLM_MAX_RETRIES = 0

logger = logging.getLogger(__name__)

_MEMORY_LOCKS: dict[str, threading.RLock] = {}
_MEMORY_LOCKS_GUARD = threading.Lock()


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
        self._memory_lock = _memory_lock_for(self.memory_path)

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
        if _is_placeholder_selection(selected_text):
            return SelectionExplanation(
                status="DEGRADED",
                answer=(
                    "这段内容是旧版本生成的占位概括，不是可以解释的论文原文。"
                    "请重新进入这篇论文的最新深读结果，再选中具体的正文或卡片内容。"
                ),
                warnings=[_warning("STALE_SELECTION_PLACEHOLDER", "旧版本占位文本不能作为论文证据。")],
            )

        evidence = self._best_evidence(selected_text)
        warnings: list[WarningItem] = []
        status = "SUCCESS"
        raw_confidence = evidence.get("score")
        confidence = float(raw_confidence) if isinstance(raw_confidence, (int, float)) else 0.0
        if not evidence.get("evidence_ref"):
            status = "DEGRADED"
            warnings.append(_warning("NO_TRACEABLE_EVIDENCE", "这段选中文本没有匹配到可追踪的 evidence_ref。"))
        elif confidence < 0.2:
            status = "DEGRADED"
            warnings.append(_warning("LOW_SELECTION_MATCH", "这段选中文本和证据片段的匹配度偏低。"))

        claim_text = str(evidence.get("claim_text") or evidence.get("text") or selected_text)
        taught_claim_text = _teach_phrase(claim_text, max_chars=220)
        section = str(evidence.get("section") or "当前论文")
        section_label = _user_facing_section_label(section)
        answer = (
            f"这段内容最接近论文中“{section_label}”部分的证据。"
            f"它支撑的局部论断是：{taught_claim_text}"
        )
        if question:
            answer += "\n\n" + _selection_followup_answer(
                question=question,
                selected_text=selected_text,
                claim_text=claim_text,
                section=section,
            )

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
            meaning=_teach_phrase(matched_symbol[1]) if symbol else full_explanation,
            source_sentence=_teach_phrase(_clean(formula.get("purpose")) or _clean(formula.get("plain_summary"))),
            intuition=_teach_phrase(_clean(formula.get("intuition")) or _clean(formula.get("plain_summary"))),
            numeric_example=_teach_phrase(_clean(formula.get("numeric_example"))),
            role_in_method=_teach_phrase(_clean(formula.get("what_if_removed")) or _clean(formula.get("purpose"))),
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
        answer_mode = _clean(payload.get("answer_mode")) or "enhanced"
        conversation_history = _conversation_history(payload.get("conversation_history"))
        if not question and selected_text:
            question = f"请解释这段内容：{selected_text}"
        if not question:
            return InteractiveAnswer(
                status="DEGRADED",
                answer="还没有收到问题。",
                uncertainty="M4 需要一个问题，或者需要你先选中一段论文内容。",
                warnings=[_warning("QUESTION_MISSING", "缺少 question。")],
            )
        if selected_text and _is_placeholder_selection(selected_text):
            return InteractiveAnswer(
                status="DEGRADED",
                answer=(
                    "你选中的内容是旧版本生成的占位概括，并不是论文原文，所以 M4 不会继续解释或猜测。"
                    "系统会优先打开这篇论文最新的重解析结果；请从新的论文卡片或正文中重新选择。"
                ),
                evidence_refs=[],
                uncertainty="占位文本没有可验证的论文证据。",
                follow_up_suggestions=[
                    "这篇论文真正解决了什么问题？",
                    "SmartRoot 的核心方法是什么？",
                    "请解释 SmartRoot 如何减少人工分析耗时。",
                ],
                used_context={"memory": False, "artifacts": False, "llm": False},
                warnings=[_warning("STALE_SELECTION_PLACEHOLDER", "旧版本占位文本不能作为论文证据。")],
            )
        conversation_focus = self._conversation_focus(
            question=question,
            selected_text=selected_text,
            conversation_history=conversation_history,
        )
        effective_question = _clean(conversation_focus.get("resolved_question")) or question
        continued_from_history = bool(conversation_focus.get("continued_from_history"))
        if not selected_text and _is_non_paper_question(question):
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
        if not selected_text and _is_underspecified_question(question) and not continued_from_history:
            paper_card = _as_dict(self.artifacts.get("paper_card"))
            return InteractiveAnswer(
                status="DEGRADED",
                answer=_clarifying_question_answer(question, paper_card),
                evidence_refs=[],
                memory_refs=[],
                uncertainty="这个问题还不够具体，M4 先追问澄清，避免把论文内容硬套到你的问题上。",
                follow_up_suggestions=_clarifying_follow_ups(paper_card),
                used_context={"memory": False, "artifacts": False, "llm": False},
                warnings=[_warning("QUESTION_UNDERSPECIFIED", "问题太宽或指代不清，需要先澄清。")],
            )

        is_formula_question = _is_formula_question(effective_question, selected_text)
        ignore_selection = _should_ignore_selection(effective_question, selected_text)
        memory_hit = self._memory_hit(question=effective_question, selected_text=selected_text)
        memory_claims = self._claims_from_memory(memory_hit) if memory_hit is not None else []
        if (
            memory_hit is not None
            and memory_claims
            and self.llm_client is None
            and not is_formula_question
            and not _looks_like_english_answer(memory_hit.answer)
            and not _is_low_quality_memory_answer(memory_hit)
            and not _is_too_thin_paper_level_memory_answer(memory_hit, question)
            and not _answer_exposes_internal_refs(memory_hit.answer)
            and not _looks_like_mojibake_answer(memory_hit.answer)
            and not _memory_conflicts_with_paper_intent(memory_hit, question)
        ):
            return InteractiveAnswer(
                status="SUCCESS",
                answer=_strip_internal_refs_from_answer(_normalize_answer_text(memory_hit.answer, max_chars=1800)),
                evidence_refs=_unique([ref for claim in memory_claims for ref in claim.evidence_refs]),
                claims=memory_claims,
                memory_refs=[memory_hit.memory_id],
                uncertainty="这次回答来自 M4 记忆，并沿用当时记录的证据引用。",
                follow_up_suggestions=_follow_ups(),
                used_context={"memory": True, "artifacts": False, "llm": False},
                context_trace=M4ContextTrace(
                    scope="selection" if selected_text else "paper",
                    continued_from_history=continued_from_history,
                    focus_question=effective_question,
                    evidence_count=len(_unique([ref for claim in memory_claims for ref in claim.evidence_refs])),
                    selected_text_used=bool(selected_text),
                ),
            )

        formula = self._formula_from_text(question=effective_question, selected_text=selected_text) if is_formula_question else None
        if formula is not None:
            answer, evidence_refs, confidence, warnings = self._answer_from_formula_card(formula)
        elif selected_text and not ignore_selection:
            selection = self.explain_selection({"selected_text": selected_text, "user_question": question})
            answer = selection.answer
            evidence_refs = selection.cited_evidence_refs
            warnings = selection.warnings
            confidence = selection.confidence
        else:
            answer, evidence_refs, confidence, warnings = self._answer_from_artifacts(effective_question)

        grounded_claims = (
            [
                GroundedClaim(
                    text=answer,
                    evidence_refs=_unique(evidence_refs),
                    support_status="ARTIFACT_DERIVED",
                )
            ]
            if answer and evidence_refs
            else []
        )
        grounding_degraded = any(
            warning.code in {"LIMITATION_EVIDENCE_MISSING", "M4_EXAMPLE_EVIDENCE_INSUFFICIENT"}
            for warning in warnings
        )
        llm_uncertainty = ""

        if answer_mode == "evidence_only":
            return InteractiveAnswer(
                status="SUCCESS" if evidence_refs and not grounding_degraded else "DEGRADED",
                answer=answer,
                evidence_refs=evidence_refs,
                claims=grounded_claims,
                uncertainty=(
                    "当前先显示论文证据能够直接支持的内容；模型增强仍可继续补充。"
                    if evidence_refs
                    else "当前论文卡片没有找到能直接支持这个问题的证据。"
                ),
                follow_up_suggestions=_follow_ups(),
                used_context={"memory": False, "artifacts": True, "llm": False},
                context_trace=M4ContextTrace(
                    scope="selection" if selected_text else "paper",
                    continued_from_history=continued_from_history,
                    focus_question=effective_question,
                    evidence_count=len(evidence_refs),
                    selected_text_used=bool(selected_text),
                ),
                warnings=warnings,
            )

        llm_evidence_refs = self._expanded_question_evidence_refs(
            question=effective_question,
            selected_text=selected_text,
            seed_refs=[*evidence_refs, *_string_list(conversation_focus.get("continuity_evidence_refs"))],
        )
        used_context = {"memory": False, "artifacts": True, "llm": False}
        if continued_from_history:
            used_context["conversation"] = True
        follow_up_suggestions = _follow_ups()
        llm_result = self._answer_with_grounded_llm(
            question=question,
            selected_text=selected_text,
            allowed_evidence_refs=llm_evidence_refs or evidence_refs,
            conversation_history=conversation_history,
            conversation_focus=conversation_focus,
        )
        if llm_result.get("ok"):
            answer = _clean(llm_result.get("answer"))
            evidence_refs = _string_list(llm_result.get("evidence_refs"))
            raw_grounded_claims = llm_result.get("claims", [])
            grounded_claims = (
                [claim for claim in raw_grounded_claims if isinstance(claim, GroundedClaim)]
                if isinstance(raw_grounded_claims, list)
                else []
            )
            grounding_degraded = bool(llm_result.get("degraded"))
            llm_uncertainty = _clean(llm_result.get("uncertainty"))
            raw_warnings = llm_result.get("warnings", [])
            if isinstance(raw_warnings, list):
                warnings.extend(warning for warning in raw_warnings if isinstance(warning, WarningItem))
            used_context = {"memory": False, "artifacts": True, "llm": True}
            if continued_from_history:
                used_context["conversation"] = True
            follow_up_suggestions = _string_list(llm_result.get("follow_up_suggestions")) or _follow_ups()
            raw_llm_confidence = llm_result.get("confidence")
            llm_confidence = (
                float(raw_llm_confidence) if isinstance(raw_llm_confidence, (int, float)) else 0.0
            )
            confidence = max(confidence, llm_confidence)
        elif self.llm_client is not None:
            code = str(llm_result.get("code") or "M4_LLM_FAILED")
            message = str(llm_result.get("message") or "LLM did not return a usable answer.")
            detail = str(llm_result.get("detail") or "")
            unsafe_artifact_warning_codes = {
                "LOW_SELECTION_MATCH",
                "NO_TRACEABLE_EVIDENCE",
                "STALE_SELECTION_PLACEHOLDER",
            }
            can_use_verified_artifacts = bool(
                evidence_refs
                and grounded_claims
                and not any(warning.code in unsafe_artifact_warning_codes for warning in warnings)
                and code
                in {
                    "M4_LLM_TIMEOUT",
                    "M4_LLM_REQUEST_FAILED",
                    "M4_CLAIM_UNSUPPORTED",
                    "M4_LLM_LOW_QUALITY",
                    "M4_LLM_INVALID_JSON",
                    "M4_LLM_INVALID_STRUCTURE",
                    "M4_LLM_EMPTY",
                }
            )
            if can_use_verified_artifacts:
                grounding_degraded = True
                if code in {"M4_LLM_TIMEOUT", "M4_LLM_REQUEST_FAILED"}:
                    llm_uncertainty = (
                        "大模型增强解释未在时限内完成；当前内容来自已定位的论文证据，"
                        "没有使用未经验证的模型输出。"
                    )
                else:
                    llm_uncertainty = (
                        "模型增强内容没有通过逐条证据校验；当前保留的是本地已定位的论文证据答案，"
                        "未展示被拒绝的模型内容。"
                    )
                warnings.append(
                    _warning(
                        code,
                        "模型增强未通过或未完成，已保留经证据校验的本地答案。",
                        detail=detail,
                    )
                )
            else:
                return InteractiveAnswer(
                    status="DEGRADED",
                    answer=_llm_failure_answer(code=code, message=message),
                    evidence_refs=[],
                    claims=[],
                    uncertainty="M4 已经拿到论文上下文，但 LLM 没有返回可用解释；本次没有改用本地兜底答案。",
                    follow_up_suggestions=_follow_ups(),
                    used_context={"memory": False, "artifacts": bool(llm_evidence_refs or evidence_refs), "llm": False},
                    context_trace=M4ContextTrace(
                        scope="selection" if selected_text else "paper",
                        continued_from_history=continued_from_history,
                        focus_question=effective_question,
                        evidence_count=len(llm_evidence_refs or evidence_refs),
                        selected_text_used=bool(selected_text),
                    ),
                    warnings=[*warnings, _warning(code, message, detail=detail)],
                )

        status = "SUCCESS" if evidence_refs and not grounding_degraded else "DEGRADED"
        if llm_uncertainty:
            uncertainty = llm_uncertainty
        elif evidence_refs and not grounding_degraded:
            uncertainty = "回答基于当前 M2 证据卡片。"
        elif evidence_refs:
            uncertainty = "部分结论无法通过逐条证据校验，未通过的内容已删除。"
        else:
            uncertainty = "没有可追踪的 evidence_ref，所以只给出受限回答。"
        result = InteractiveAnswer(
            status=status,
            answer=answer,
            evidence_refs=evidence_refs,
            claims=grounded_claims,
            uncertainty=uncertainty,
            follow_up_suggestions=follow_up_suggestions,
            used_context=used_context,
            context_trace=M4ContextTrace(
                scope="selection" if selected_text else "paper",
                continued_from_history=continued_from_history,
                focus_question=effective_question,
                evidence_count=len(evidence_refs),
                selected_text_used=bool(selected_text),
            ),
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
            metadata={
                "selected_text": selected_text,
                "status": result.status,
                "grounded_claims": [claim.model_dump(mode="json") for claim in result.claims],
            },
        )
        return result

    def advisor_question(self, payload: dict[str, object]) -> AdvisorQuestion:
        mode = _clean(payload.get("advisor_mode")) or "group_meeting"
        user_question = _compact_user_text(
            payload.get("user_question") or payload.get("focus_question") or payload.get("question"),
            max_chars=600,
        )
        selected_text = _compact_user_text(payload.get("selected_text"), max_chars=900)
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        method = _claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea"))
        problem = _claim_text(paper_card.get("problem"))
        core_idea = _claim_text(paper_card.get("core_idea"))
        evidence_ref = _claim_ref(paper_card.get("method_overview")) or _claim_ref(paper_card.get("core_idea")) or self._first_evidence_ref()
        if not method:
            return AdvisorQuestion(
                status="DEGRADED",
                question="paper_card.method_overview 缺失，M4 暂时不能生成有证据支撑的组会追问。",
                warnings=[_warning("ADVISOR_EVIDENCE_MISSING", "paper_card 中缺少方法相关证据。")],
            )

        difficulty = "hard" if mode in {"defense", "qualifying_exam"} else "medium"
        if user_question:
            question = (
                f"围绕你自己的问题“{user_question}”，请先用这篇论文给出回答；"
                f"再说明论文中的“{method}”怎样支撑这个回答。"
                "如果组会上继续追问，请把你的问题、论文机制和证据依据各讲清楚一句。"
            )
            if selected_text:
                question += f" 可以优先结合你选中的这段内容：“{_compact_user_text(selected_text, max_chars=180)}”。"
        else:
            question = (
                f"如果组会上有人追问：这篇论文为什么认为“{method}”能回应"
                f"{'“' + problem + '”这个问题' if problem else '它提出的研究问题'}？"
                "请用 30 秒回答，把问题、机制和论文证据各讲清楚一句。"
            )
        expected_points = _advisor_expected_points_from_claims(
            problem=problem,
            method=method,
            core_idea=core_idea,
        )
        if user_question:
            expected_points = [
                f"先直接回答“{user_question}”，不要换成泛泛的论文概述。",
                *expected_points,
            ]
            answer_format = [
                "先用一句自然话回答你真正想问的点",
                "再把论文里的机制或发现解释成能听懂的因果链",
                "最后补一句：这个判断主要靠哪类正文证据支撑",
            ]
        else:
            answer_format = ["先说明论文真正卡住的地方", "再讲方法怎么接上这个困难", "最后补一句它依靠哪类正文证据"]
        result = AdvisorQuestion(
            question=question,
            user_question=user_question,
            target_concept=user_question or method,
            difficulty=difficulty,
            expected_answer_points=expected_points,
            why_it_matters="这个问题检查你有没有把论文的研究问题、方法机制和证据链连成一条线，而不是只背方法名。",
            answer_format=answer_format,
            evidence_refs=_list_of_one(evidence_ref),
            question_type="custom_focus" if user_question else "method",
            follow_up_policy="deeper" if mode != "qualifying_exam" else "redirect_then_deeper",
            warnings=[] if evidence_ref else [_warning("ADVISOR_EVIDENCE_MISSING", "这个追问没有附带 evidence_ref。")],
        )
        if user_question:
            result.why_it_matters = "这个问题检查你能不能把自己的疑问和论文证据接起来，而不是脱离论文泛泛回答。"
        self._append_memory(
            memory_type="advisor_question",
            text=result.target_concept,
            question=result.question,
            answer="",
            evidence_refs=result.evidence_refs,
            confidence=0.8 if result.evidence_refs else 0.35,
            source_artifact="paper_card",
            metadata={
                "advisor_mode": mode,
                "question_type": result.question_type,
                "user_question": user_question,
                "selected_text": selected_text,
            },
        )
        return result

    def advisor_evaluate(self, payload: dict[str, object]) -> AdvisorEvaluation:
        answer = _clean(payload.get("user_answer") or payload.get("answer"))
        question = _clean(payload.get("question"))
        evidence_refs = _string_list(payload.get("evidence_refs")) or _list_of_one(self._first_evidence_ref())
        expected = _string_list(payload.get("expected_answer_points"))
        if not expected:
            expected = self._advisor_expected_points()

        covered, missing = _advisor_point_coverage(answer=answer, expected_points=expected)
        score = _advisor_score(answer=answer, covered_count=len(covered), total_count=len(expected))
        misconceptions = _advisor_misconceptions(answer)
        improvement_steps = _advisor_improvement_steps(missing)
        feedback = _advisor_feedback(answer=answer, score=score, covered=covered, missing=missing)
        next_question = _advisor_next_question(missing)
        result = AdvisorEvaluation(
            score=round(score, 2),
            covered_points=covered,
            missing_points=missing[:4],
            misconceptions=misconceptions,
            improvement_steps=improvement_steps,
            next_question=next_question,
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
        with self._memory_lock:
            current = self._read_memory_unlocked()
            bundle = M4MemoryBundle(job_id=self.job_id, warnings=current.warnings)
            self._write_memory_unlocked(bundle)
            return bundle

    def _conversation_focus(
        self,
        *,
        question: str,
        selected_text: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, object]:
        """Resolve follow-up language without treating chat history as paper evidence."""

        recent_history = conversation_history[-8:]
        previous_user_question = next(
            (
                item["content"]
                for item in reversed(recent_history)
                if item.get("role") == "user" and item.get("content")
            ),
            "",
        )
        previous_answer = next(
            (
                item["content"]
                for item in reversed(recent_history)
                if item.get("role") == "assistant" and item.get("content")
            ),
            "",
        )
        continued = bool(previous_user_question) and (
            _is_underspecified_question(question) or _has_followup_reference(question)
        )
        resolved_question = question
        continuity_refs: list[str] = []
        if continued:
            resolved_question = (
                f"上一轮讨论的问题是“{_compact_user_text(previous_user_question, max_chars=420)}”。"
                f"用户现在追问“{question}”。请把当前追问理解为上一轮话题的延续。"
            )
            for record in reversed(self._read_memory().records):
                if record.memory_type != "interactive_answer" or not record.evidence_refs:
                    continue
                continuity_refs = record.evidence_refs[:4]
                break
        return {
            "continued_from_history": continued,
            "resolved_question": _compact_user_text(resolved_question, max_chars=1000),
            "prior_user_question": _compact_user_text(previous_user_question, max_chars=420) if continued else "",
            "prior_answer_summary": _compact_user_text(previous_answer, max_chars=700) if continued else "",
            "continuity_evidence_refs": continuity_refs,
            "selected_text_used": bool(selected_text),
        }

    def _expanded_question_evidence_refs(
        self,
        *,
        question: str,
        selected_text: str,
        seed_refs: list[str],
        limit: int = 8,
    ) -> list[str]:
        blocked_formula_refs = self._blocked_formula_evidence_refs()
        refs = [ref for ref in _unique(seed_refs) if ref not in blocked_formula_refs]
        if _should_include_formula_context(question, selected_text):
            for ref in self._formula_card_refs(limit=5):
                if ref not in refs:
                    refs.append(ref)
                if len(refs) >= limit:
                    break
        query = f"{question} {selected_text}".strip()
        for candidate, score in self._ranked_evidence_candidates(query):
            ref = _clean(candidate.get("evidence_ref"))
            if not ref or ref in refs or ref in blocked_formula_refs:
                continue
            if score < 0.08 and refs:
                continue
            refs.append(ref)
            if len(refs) >= limit:
                break
        if not refs:
            refs.extend(self._paper_card_refs())
        return _unique(refs)[:limit]

    def _answer_with_grounded_llm(
        self,
        *,
        question: str,
        selected_text: str,
        allowed_evidence_refs: list[str],
        conversation_history: list[dict[str, str]],
        conversation_focus: dict[str, object],
    ) -> dict[str, object]:
        if self.llm_client is None:
            return _llm_error_result("M4_LLM_DISABLED", "当前没有启用 M4 LLM 客户端。")
        if not allowed_evidence_refs:
            return _llm_error_result("M4_CONTEXT_MISSING", "没有可传给 M4 的论文证据引用。")

        allowed = set(allowed_evidence_refs)
        evidence_rows = self._llm_context(allowed, query=f"{question} {selected_text}".strip())
        if not evidence_rows:
            return _llm_error_result("M4_CONTEXT_MISSING", "没有可传给 M4 的可验证论文证据。")
        evidence_by_ref = _evidence_text_by_ref(evidence_rows)
        support_text_by_ref = _claim_support_text_by_ref(evidence_rows)
        source_quotes_by_id = _source_quotes_by_id(evidence_rows)
        context = {
            "retrieved_evidence": evidence_rows,
            "recent_memory": self._memory_context(),
            "conversation_history": conversation_history[-8:],
            "conversation_focus": {
                "continued_from_history": bool(conversation_focus.get("continued_from_history")),
                "resolved_question": _compact_user_text(conversation_focus.get("resolved_question"), max_chars=1000),
                "prior_user_question": _compact_user_text(conversation_focus.get("prior_user_question"), max_chars=420),
                "prior_answer_summary": _compact_user_text(conversation_focus.get("prior_answer_summary"), max_chars=700),
            },
            "allowed_evidence_refs": allowed_evidence_refs,
        }
        prompt = {
            "question": _compact_user_text(question, max_chars=900),
            "selected_text": _compact_user_text(selected_text, max_chars=900),
            "context": context,
            "output_rules": [
                "只输出符合 required_json_schema 的 JSON。",
                "每个可向用户展示的结论必须单独放进 claims，不能把整篇回答只绑定到一个引用集合。",
                "每个 claim 的 evidence_refs 只能从 allowed_evidence_refs 选择，并逐个提供 supporting_quotes。",
                "supporting_quotes 优先填写对应 retrieved_evidence 的 quote_id；不要自行复制、改写或翻译长原文。",
                "如果没有 quote_id，quote 才必须从对应 evidence_ref 的 text 原样摘录。",
                "claim.text 必须是简体中文自然语言，不能暴露 evidence_ref、memory_ref、job id 等内部编号。",
                "公式、阈值、数值、数据集、指标和实验结果只有在 supporting quote 明确出现时才允许写入。",
                "玩具数字只能放在 toy_example claim 中，且计算规则必须在引用证据里明确出现。",
                "证据不足的细节不要猜；写进顶层 uncertainty，而不是伪造 claim。",
                "conversation_history 和 recent_memory 只用于理解指代与追问，不能作为论文事实或 supporting quote。",
                "如果 conversation_focus.continued_from_history 为 true，要直接承接上一轮话题，不要再次追问“这个指什么”。",
            ],
            "required_json_schema": {
                "claims": [
                    {
                        "text": "一个独立、可核验的简体中文结论",
                        "claim_type": "paper_claim | explanation | toy_example",
                        "evidence_refs": ["一个或多个允许的引用"],
                        "supporting_quotes": [
                            {
                                "evidence_ref": "与该 quote 对应的允许引用",
                                "quote_id": "从 retrieved_evidence 原样选择的 quote_id",
                                "quote": "仅在没有 quote_id 时，从该引用 text 原样复制的最小充分片段",
                            }
                        ],
                        "uncertainty": "该结论自身的不确定性；充分时为空字符串",
                    }
                ],
                "uncertainty": "对证据缺口的简体中文说明",
                "follow_up_suggestions": ["基于现有论文证据可以继续追问的问题"],
            },
        }
        if _is_problem_solution_question(question):
            prompt["output_rules"].append(
                "当前问题询问论文真正面对的研究问题或痛点；至少一条 claim 必须明确说明现有做法的困难、"
                "限制或未满足需求，不能只复述新方法的步骤、模块或功能。"
            )
        if selected_text:
            prompt["output_rules"].append(
                "当前问题包含选中文本；第一条 claim 必须直接解释 selected_text 的含义和它在论文中的作用，"
                "不能改答相邻段落、泛化到整篇论文，或只罗列无关方法细节。"
            )
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是 ResearchSensei 的 M4 论文助教。你只能根据提供的逐条证据生成 claim。"
                    "每条 claim 都必须逐引用绑定原文 quote；合法引用不等于内容获得支持。"
                    "不要引入证据里没有的算法、公式、阈值、数值、数据集、指标或实验结果。"
                    "对话历史只能帮助理解追问，绝不能替代 retrieved_evidence。"
                    "只能返回 JSON，不要输出 Markdown。"
                ),
            ),
            ChatMessage(role="user", content=json.dumps(prompt, ensure_ascii=False)),
        ]
        try:
            chat_json = getattr(
                self.llm_client,
                "chat_json_with_repair",
                self.llm_client.chat_json,
            )
            data = _run_async_llm(
                chat_json(
                    messages,
                    config=LLMConfig(
                        temperature=0.15,
                        max_tokens=_m4_output_token_budget(self.llm_client),
                        json_mode=True,
                        timeout=M4_LLM_TIMEOUT_SECONDS,
                        max_retries=M4_LLM_MAX_RETRIES,
                        retry_delay=1.0,
                        disable_thinking=True,
                    ),
                )
            )
        except (LLMClientError, RuntimeError, ValueError, TypeError) as exc:
            logger.warning("M4 grounded LLM request failed for job %s: %s", self.job_id, exc, exc_info=True)
            error_text = str(exc).lower()
            if "json" in error_text or "parse" in error_text:
                return _llm_error_result(
                    "M4_LLM_INVALID_JSON",
                    "模型连续两次返回了无法验证的结构化格式；原始输出已隐藏。",
                )
            if "timeout" in error_text or "timed out" in error_text:
                return _llm_error_result("M4_LLM_TIMEOUT", "模型服务响应超时，请稍后重试。")
            return _llm_error_result(
                "M4_LLM_REQUEST_FAILED",
                "模型服务请求失败；详细响应未向界面暴露。",
            )
        if not isinstance(data, dict):
            return _llm_error_result("M4_LLM_INVALID_STRUCTURE", "LLM 没有返回 claim 结构。")

        raw_claims = data.get("claims", [])
        if not isinstance(raw_claims, list) or not raw_claims:
            return _llm_error_result("M4_LLM_INVALID_STRUCTURE", "LLM 返回的 claims 为空或格式错误。")
        claims: list[GroundedClaim] = []
        rejected_reasons: list[str] = []
        for raw_claim in raw_claims[:12]:
            claim, reason = _validate_grounded_claim(
                raw_claim,
                allowed=allowed,
                evidence_by_ref=evidence_by_ref,
                support_text_by_ref=support_text_by_ref,
                source_quotes_by_id=source_quotes_by_id,
            )
            if claim is None:
                rejected_reasons.append(reason)
                continue
            claims.append(claim)
        if not claims:
            return _llm_error_result(
                "M4_CLAIM_UNSUPPORTED",
                "LLM 给出了合法引用，但没有任何结论通过内容级证据校验。",
                detail="; ".join(_unique(rejected_reasons)[:6]),
            )

        answer = _soften_mechanical_answer("\n\n".join(claim.text for claim in claims))
        if not answer:
            return _llm_error_result("M4_LLM_EMPTY", "通过证据校验的结论为空。")
        if _looks_like_english_answer(answer):
            return _llm_error_result("M4_LLM_LOW_QUALITY", "LLM 返回了英文占比过高的回答。")
        if _looks_like_thin_llm_answer(answer):
            return _llm_error_result("M4_LLM_LOW_QUALITY", "LLM 返回的回答过于空泛。")
        if _should_reject_llm_answer_for_question(question, answer, context=context):
            return _llm_error_result("M4_LLM_LOW_QUALITY", "LLM 回答没有满足当前问题的证据约束或具体性要求。")
        if selected_text and not _answer_aligned_with_selection(answer, selected_text):
            return _llm_error_result("M4_LLM_LOW_QUALITY", "LLM 回答没有直接解释用户选中的内容。")

        warnings: list[WarningItem] = []
        if rejected_reasons:
            warnings.append(
                WarningItem(
                    code="M4_CLAIM_UNSUPPORTED",
                    message="部分 LLM 结论未通过内容级证据校验，已从回答中删除。",
                    detail="; ".join(_unique(rejected_reasons)[:6]),
                )
            )
        uncertainty = _compact_user_text(data.get("uncertainty"), max_chars=500)
        if rejected_reasons and not uncertainty:
            uncertainty = "部分结论缺少能直接支持其内容的论文证据，已删除。"
        return {
            "ok": True,
            "answer": answer,
            "claims": claims,
            "evidence_refs": _unique([ref for claim in claims for ref in claim.evidence_refs]),
            "confidence": 0.7 if rejected_reasons else 0.88,
            "degraded": bool(rejected_reasons),
            "uncertainty": uncertainty,
            "warnings": warnings,
            "follow_up_suggestions": _paper_follow_up_suggestions(data.get("follow_up_suggestions")),
        }

    def _answer_from_artifacts(self, question: str) -> tuple[str, list[str], float, list[WarningItem]]:
        lower = question.lower()
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        ranked_evidence = [
            candidate
            for candidate, score in self._ranked_evidence_candidates(question)
            if score >= 0.08 and not _is_front_matter_candidate(candidate)
        ][:3]
        if _question_wants_example(question):
            answer = _example_driven_paper_answer(paper_card, question=question, evidence_rows=ranked_evidence)
            refs = _primary_paper_card_refs(paper_card) or self._paper_card_refs()
            if answer and refs:
                return (
                    answer,
                    refs[:4],
                    0.55,
                    [
                        _warning(
                            "M4_EXAMPLE_EVIDENCE_INSUFFICIENT",
                            "当前证据不足以构造可复算的数值例子；回答已限制为论文卡片中的任务和方法。",
                        )
                    ],
                )
        if _is_problem_solution_question(question):
            answer = _problem_solution_answer(paper_card, question=question, evidence_rows=ranked_evidence)
            refs = _primary_paper_card_refs(paper_card) or self._paper_card_refs()
            if answer and refs:
                return answer, refs[:4], 0.84, []
        if _is_limitation_question(question) and not _claim_text(paper_card.get("limitations")):
            refs = _primary_paper_card_refs(paper_card) or self._paper_card_refs()
            return (
                _missing_limitation_answer(paper_card, question=question, evidence_rows=ranked_evidence),
                refs[:3],
                0.45 if refs else 0.2,
                [_warning("LIMITATION_EVIDENCE_MISSING", "当前论文卡片没有可追踪的局限证据。")],
            )
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
            answer = _structured_paper_answer(
                paper_card,
                focus="对应证据",
                question=question,
                evidence_rows=ranked_evidence,
            )
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
                    answer = _structured_paper_answer(
                        paper_card,
                        focus=label,
                        question=question,
                        evidence_rows=ranked_evidence,
                    )
                    refs = _primary_paper_card_refs(paper_card) or _list_of_one(ref)
                    return answer or f"关于“{label}”：{text}", refs, 0.82 if refs else 0.4, []
        summary = _usable_card_text(paper_card.get("one_sentence_summary")) or _usable_card_text(
            paper_card.get("thirty_second")
        )
        refs = _primary_paper_card_refs(paper_card) or self._paper_card_refs()
        if summary:
            return (
                _structured_paper_answer(
                    paper_card,
                    focus="论文核心",
                    question=question,
                    evidence_rows=ranked_evidence,
                )
                or f"论文层面的回答：{summary}",
                refs[:2],
                0.75 if refs else 0.35,
                [],
            )
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

    def _paper_overview_context(self) -> dict[str, object]:
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        overview: dict[str, object] = {}
        for key in [
            "title",
            "one_sentence_summary",
            "thirty_second",
            "problem",
            "core_idea",
            "method_overview",
            "experiment_summary",
            "limitations",
            "background",
            "bottleneck",
        ]:
            value = paper_card.get(key)
            if isinstance(value, dict):
                text = _claim_text(value)
                if text:
                    overview[key] = {
                        "text": _compact_user_text(text, max_chars=1000),
                        "evidence_ref": _claim_ref(value),
                    }
            else:
                text = _clean(value)
                if text:
                    overview[key] = _compact_user_text(text, max_chars=1000)
        return overview

    def _memory_context(self, limit: int = 4) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for record in reversed(self._read_memory().records):
            if record.memory_type != "interactive_answer":
                continue
            if _is_low_quality_memory_answer(record) or _looks_like_mojibake_answer(record.answer):
                continue
            rows.append({
                "question": _compact_user_text(record.question, max_chars=500),
                "answer": _compact_user_text(record.answer, max_chars=800),
                "evidence_refs": record.evidence_refs[:4],
            })
            if len(rows) >= limit:
                break
        return rows

    def _llm_context(self, allowed_refs: set[str], *, query: str = "") -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        paper_card = _as_dict(self.artifacts.get("paper_card"))
        for field, claim in _paper_claims(paper_card):
            ref = _claim_ref(claim)
            text = _claim_text(claim)
            if ref in allowed_refs and text:
                rows.append({"source": f"paper_card.{field}", "evidence_ref": ref, "text": _compact_user_text(text, max_chars=900)})
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            formulas = []
        formula_rows: list[dict[str, str]] = []
        for formula in formulas:
            if not isinstance(formula, dict):
                continue
            ref = _clean(formula.get("evidence_ref"))
            if ref not in allowed_refs:
                continue
            text = _formula_context_text(formula)
            if text:
                formula_rows.append({"source": "formula_cards", "evidence_ref": ref, "text": _compact_user_text(text, max_chars=900)})
        formula_first = _should_include_formula_context(query, "")
        if formula_first:
            # Formula questions must not lose their exact source expression
            # merely because several prose passages share one evidence ref.
            rows.extend(formula_rows)
        ranked_candidates = (
            self._ranked_evidence_candidates(query)
            if query
            else [(candidate, 0.0) for candidate in self._evidence_candidates()]
        )
        for candidate, _score in ranked_candidates:
            ref = _clean(candidate.get("evidence_ref"))
            if ref not in allowed_refs:
                continue
            text = _clean(candidate.get("claim_text")) or _clean(candidate.get("quote_or_summary")) or _clean(candidate.get("text"))
            if text:
                rows.append({
                    "source": _clean(candidate.get("artifact_source")) or "claim_evidence",
                    "evidence_ref": ref,
                    "text": _focused_evidence_excerpt(text, query=query, max_chars=900),
                    "passage_id": _clean(candidate.get("passage_id")),
                })
        if not formula_first:
            rows.extend(formula_rows)
        unique_rows: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            passage_id = _clean(row.get("passage_id"))
            key = (
                "passage" if passage_id else row["source"],
                passage_id or f"{row['evidence_ref']}:{_quote_key(row['text'])}",
            )
            if key in seen:
                continue
            row.pop("passage_id", None)
            unique_rows.append(row)
            seen.add(key)
            if len(unique_rows) >= 8:
                break
        return _with_source_quote_ids(unique_rows)

    def _formula_card_refs(self, limit: int = 5) -> list[str]:
        refs: list[str] = []
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            return refs
        for formula in formulas:
            if not isinstance(formula, dict):
                continue
            if not _formula_card_is_usable(formula):
                continue
            ref = _clean(formula.get("evidence_ref"))
            if ref:
                refs.append(ref)
            if len(_unique(refs)) >= limit:
                break
        return _unique(refs)[:limit]

    def _blocked_formula_evidence_refs(self) -> set[str]:
        refs: set[str] = set()
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            return refs
        for formula in formulas:
            if not isinstance(formula, dict) or _formula_card_is_usable(formula):
                continue
            ref = _clean(formula.get("evidence_ref"))
            if ref:
                refs.add(ref)
        return refs

    def _best_evidence(self, text: str) -> dict[str, object]:
        candidates = [
            candidate
            for candidate in self._evidence_candidates()
            if _candidate_text(candidate) and not _is_unreliable_evidence_candidate(candidate)
        ]
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

    def _ranked_evidence_candidates(self, query: str) -> list[tuple[dict[str, object], float]]:
        candidates = self._evidence_candidates()
        if not candidates:
            return []
        query_terms = _expanded_query_terms(query)
        normalized_query = _normalize(query)
        ranked: list[tuple[dict[str, object], float]] = []
        for candidate in candidates:
            if _is_unreliable_evidence_candidate(candidate):
                continue
            haystack = _candidate_text(candidate)
            haystack_terms = _expanded_query_terms(haystack)
            overlap = len(query_terms & haystack_terms)
            score = overlap / max(len(query_terms), 1)
            haystack_lower = haystack.lower()
            for term in query_terms:
                if len(term) >= 4 and term in haystack_lower:
                    score += 0.04
            if normalized_query and normalized_query in _normalize(haystack):
                score += 0.35
            if _is_list_question(query):
                # A generic "list of" may be an author list or bibliography.
                # Reward list wording only when it is tied to traits.
                if (
                    "traits included" in haystack_lower
                    or re.search(r"list of.{0,80}\btraits?\b", haystack_lower, flags=re.DOTALL)
                    or re.search(r"\btraits?\s+(?:include|includes|included)\b", haystack_lower)
                ):
                    score += 0.7
                elif "available traits" in haystack_lower:
                    score += 0.3
                if haystack_lower.count("trait") >= 4 or haystack_lower.count("phenotype") >= 4:
                    score += 0.12
            section = _clean(candidate.get("section")).lower()
            if any(marker in section for marker in ["front", "title", "author"]):
                score -= 0.35
            if _clean(candidate.get("claim_type")).upper() in {"METHOD", "RESULT", "FINDING"}:
                score += 0.08
            if _clean(candidate.get("artifact_source")) == "passage_index":
                score += 0.1
            if _is_problem_solution_question(query):
                problem_markers = (
                    "we present in this paper",
                    "in this study, we introduce",
                    "need for",
                    "time consuming",
                    "time-consuming",
                    "errors",
                    "root overlap",
                    "hampered",
                    "challenge",
                    "problem",
                )
                score += 0.12 * sum(marker in haystack_lower for marker in problem_markers)
            # Keep the raw score for ordering. Capping every strong match at
            # 0.99 erased the list-specific bonus and restored artifact order,
            # which could put an abstract ahead of the passage containing the
            # requested list.
            ranked.append((candidate, max(0.0, score)))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _evidence_candidates(self) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        passage_by_id: dict[str, dict[str, object]] = {}
        for passage in self._passages():
            passage_id = _clean(passage.get("passage_id"))
            if passage_id:
                passage_by_id[passage_id] = passage
            for ref in _string_list(passage.get("evidence_refs")):
                candidates.append({
                    "artifact_source": "passage_index",
                    "evidence_ref": ref,
                    "passage_id": passage_id,
                    "text": _clean(passage.get("text")) or _clean(passage.get("normalized_text")),
                    "section": _clean(passage.get("section")),
                    "source_block_types": passage.get("source_block_types", []),
                    "formula_origins": passage.get("formula_origins", []),
                    "risk_flags": passage.get("risk_flags", []),
                })
        for claim in self._claims():
            passage_id = _clean(claim.get("passage_id"))
            passage = passage_by_id.get(passage_id, {})
            candidates.append({
                "artifact_source": "claim_evidence",
                "evidence_ref": _clean(claim.get("evidence_ref")),
                "passage_id": passage_id,
                "claim_type": _clean(claim.get("claim_type")),
                "claim_text": _clean(claim.get("claim_text")),
                "quote_or_summary": _clean(claim.get("quote_or_summary")),
                "source_sentence": _clean(claim.get("source_sentence")),
                "section": _clean(claim.get("section")) or _clean(passage.get("section")),
                "text": _clean(passage.get("text")) or _clean(passage.get("normalized_text")),
                "source_block_types": passage.get("source_block_types", []),
                "formula_origins": passage.get("formula_origins", []),
                "risk_flags": claim.get("risk_flags", []) or passage.get("risk_flags", []),
            })
        for field, paper_claim in _paper_claims(_as_dict(self.artifacts.get("paper_card"))):
            ref = _claim_ref(paper_claim)
            if ref:
                candidates.append({
                    "artifact_source": "paper_card",
                    "evidence_ref": ref,
                    "claim_text": _claim_text(paper_claim),
                    "section": field,
                    "text": _claim_text(paper_claim),
                })
        return [candidate for candidate in candidates if candidate.get("evidence_ref") or candidate.get("text")]

    def _find_formula(self, formula_id: str) -> dict[str, object] | None:
        formulas = _as_dict(self.artifacts.get("formula_cards")).get("formula_cards", [])
        if not isinstance(formulas, list):
            return None
        for formula in formulas:
            if not isinstance(formula, dict):
                continue
            if not _formula_card_is_usable(formula):
                continue
            if formula_id and _clean(formula.get("formula_id")) == formula_id:
                return formula
        for formula in formulas:
            if isinstance(formula, dict) and _formula_card_is_usable(formula):
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
        return _advisor_expected_points_from_claims(
            problem=_claim_text(paper_card.get("problem")),
            method=_claim_text(paper_card.get("method_overview")),
            core_idea=_claim_text(paper_card.get("core_idea")),
        )

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
                if not self._claims_from_memory(record):
                    continue
                return record
        return None

    def _claims_from_memory(self, record: M4MemoryRecord | None) -> list[GroundedClaim]:
        if record is None:
            return []
        raw_claims = record.metadata.get("grounded_claims", [])
        if not isinstance(raw_claims, list):
            return []
        known_refs = self._known_evidence_refs()
        evidence_by_ref = _evidence_text_by_ref(self._llm_context(known_refs))
        claims: list[GroundedClaim] = []
        for raw_claim in raw_claims:
            try:
                claim = GroundedClaim.model_validate(raw_claim)
            except (TypeError, ValueError):
                continue
            refs = _unique(claim.evidence_refs)
            if (
                not claim.text
                or not refs
                or any(ref not in known_refs or ref not in evidence_by_ref for ref in refs)
            ):
                continue
            evidence_text = " ".join(
                text
                for ref in refs
                for text in evidence_by_ref.get(ref, [])
            )
            supported, _reason = _claim_content_supported(
                claim.text,
                evidence_text=evidence_text,
                claim_type=claim.claim_type,
            )
            if not supported:
                continue
            claims.append(
                claim.model_copy(
                    update={
                        "evidence_refs": refs,
                        "support_status": "MEMORY_REPLAY",
                    }
                )
            )
        return claims

    def _known_evidence_refs(self) -> set[str]:
        refs = set(self._paper_card_refs())
        refs.update(self._formula_card_refs(limit=100))
        refs.update(
            _clean(candidate.get("evidence_ref"))
            for candidate in self._evidence_candidates()
            if _clean(candidate.get("evidence_ref"))
        )
        return refs

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
        with self._memory_lock:
            bundle = self._read_memory_unlocked()
            if any(warning.code == "M4_MEMORY_CORRUPTION_UNPRESERVED" for warning in bundle.warnings):
                raise OSError("Refusing to overwrite an unpreserved corrupt M4 memory file.")
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
            self._write_memory_unlocked(bundle)
            return record

    def _read_memory(self) -> M4MemoryBundle:
        with self._memory_lock:
            return self._read_memory_unlocked()

    def _read_memory_unlocked(self) -> M4MemoryBundle:
        if not self.memory_path.exists():
            return M4MemoryBundle(job_id=self.job_id)
        try:
            if self.memory_path.stat().st_size > M4_MEMORY_MAX_BYTES:
                return self._preserve_corrupt_memory_unlocked(
                    code="M4_MEMORY_FILE_TOO_LARGE",
                    message="M4 记忆文件超过大小上限，已保留原文件并从空记忆继续。",
                )
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            bundle = _migrate_memory_payload(data, expected_job_id=self.job_id)
            return _sanitize_memory_bundle(bundle)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return self._preserve_corrupt_memory_unlocked(
                code="M4_MEMORY_CORRUPTED",
                message="M4 记忆文件损坏或不兼容，已保留原文件并从空记忆继续。",
                detail=type(exc).__name__,
            )

    def _write_memory(self, bundle: M4MemoryBundle) -> None:
        with self._memory_lock:
            self._write_memory_unlocked(bundle)

    def _write_memory_unlocked(self, bundle: M4MemoryBundle) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        bounded = _sanitize_memory_bundle(bundle)
        payload = _serialize_memory_bundle(bounded)
        temp_path = self.memory_path.with_name(f".{self.memory_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp_path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.memory_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _preserve_corrupt_memory_unlocked(
        self,
        *,
        code: str,
        message: str,
        detail: str = "",
    ) -> M4MemoryBundle:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        preserved = self.memory_path.with_name(
            f"{self.memory_path.stem}.corrupt-{timestamp}-{uuid.uuid4().hex[:8]}{self.memory_path.suffix}"
        )
        try:
            os.replace(self.memory_path, preserved)
        except OSError as exc:
            return M4MemoryBundle(
                job_id=self.job_id,
                warnings=[
                    WarningItem(
                        code="M4_MEMORY_CORRUPTION_UNPRESERVED",
                        message="M4 记忆文件损坏，且无法安全保留原文件；已拒绝覆盖。",
                        detail=type(exc).__name__,
                    )
                ],
            )
        return M4MemoryBundle(
            job_id=self.job_id,
            warnings=[
                WarningItem(
                    code=code,
                    message=message,
                    detail=f"{detail}; preserved_as={preserved.name}".strip("; "),
                )
            ],
        )


def _memory_lock_for(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.absolute()))
    with _MEMORY_LOCKS_GUARD:
        lock = _MEMORY_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _MEMORY_LOCKS[key] = lock
        return lock


def _migrate_memory_payload(data: object, *, expected_job_id: str) -> M4MemoryBundle:
    if not isinstance(data, dict):
        raise ValueError("M4 memory root must be an object.")
    version = _clean(data.get("schema_version")) or "m4_memory"
    job_id = _clean(data.get("job_id"))
    if job_id != expected_job_id:
        raise ValueError("M4 memory job_id does not match the current job.")
    if version == M4_MEMORY_SCHEMA_VERSION:
        return M4MemoryBundle.model_validate(data)
    if version not in {"m4_memory", "m4_memory.v1", "1"}:
        raise ValueError(f"Unsupported M4 memory schema: {version}")
    records = data.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Legacy M4 memory records must be a list.")
    bundle = M4MemoryBundle(
        job_id=expected_job_id,
        records=[M4MemoryRecord.model_validate(record) for record in records],
        migrated_from=version,
        warnings=[
            _warning(
                "M4_MEMORY_SCHEMA_MIGRATED",
                f"M4 记忆已从 {version} 迁移到 {M4_MEMORY_SCHEMA_VERSION}。",
            )
        ],
    )
    return bundle


def _sanitize_memory_bundle(bundle: M4MemoryBundle) -> M4MemoryBundle:
    if bundle.schema_version != M4_MEMORY_SCHEMA_VERSION:
        raise ValueError("M4 memory must use the current schema before writing.")
    records: list[M4MemoryRecord] = []
    seen: set[tuple[str, str, str, str]] = set()
    removed = 0
    for original in reversed(bundle.records):
        record = original.model_copy(
            update={
                "text": _compact_user_text(original.text, max_chars=4000),
                "question": _compact_user_text(original.question, max_chars=1000),
                "answer": _normalize_answer_text(original.answer, max_chars=4000),
                "evidence_refs": _unique(original.evidence_refs)[:16],
            },
            deep=True,
        )
        meaningful = bool(record.text or record.question or record.answer)
        low_quality = bool(record.answer) and (
            _is_low_quality_memory_answer(record) or _looks_like_mojibake_answer(record.answer)
        )
        key = (
            record.memory_type,
            _quote_key(record.question),
            _quote_key(record.answer),
            _quote_key(str(record.metadata.get("selected_text") or record.text)),
        )
        if not meaningful or low_quality or key in seen:
            removed += 1
            continue
        records.append(record)
        seen.add(key)
    records.reverse()

    warnings = _unique_warnings(bundle.warnings)
    if removed:
        warnings.append(_warning("M4_MEMORY_RECORDS_CLEANED", f"已清理 {removed} 条空白、低质量或重复 M4 记忆。"))
    if len(records) > M4_MEMORY_MAX_RECORDS:
        dropped = len(records) - M4_MEMORY_MAX_RECORDS
        records = records[-M4_MEMORY_MAX_RECORDS:]
        warnings.append(_warning("M4_MEMORY_RECORD_LIMIT", f"M4 记忆超过条数上限，已移除最早的 {dropped} 条。"))
    sanitized = M4MemoryBundle(
        job_id=bundle.job_id,
        records=records,
        migrated_from=bundle.migrated_from,
        warnings=_unique_warnings(warnings)[-M4_MEMORY_MAX_WARNINGS:],
    )
    size_dropped = 0
    while sanitized.records and len(_memory_json_bytes(sanitized)) > M4_MEMORY_MAX_BYTES:
        sanitized.records.pop(0)
        size_dropped += 1
    if size_dropped:
        sanitized.warnings.append(
            _warning(
                "M4_MEMORY_SIZE_LIMIT",
                f"M4 记忆超过文件大小上限，已移除最早的 {size_dropped} 条。",
            )
        )
        sanitized.warnings = _unique_warnings(sanitized.warnings)[-M4_MEMORY_MAX_WARNINGS:]
        while sanitized.records and len(_memory_json_bytes(sanitized)) > M4_MEMORY_MAX_BYTES:
            sanitized.records.pop(0)
            size_dropped += 1
        for index, warning in enumerate(sanitized.warnings):
            if warning.code == "M4_MEMORY_SIZE_LIMIT":
                sanitized.warnings[index] = _warning(
                    "M4_MEMORY_SIZE_LIMIT",
                    f"M4 记忆超过文件大小上限，已移除最早的 {size_dropped} 条。",
                )
                break
    while len(sanitized.warnings) > 1 and len(_memory_json_bytes(sanitized)) > M4_MEMORY_MAX_BYTES:
        sanitized.warnings.pop(0)
    if len(_memory_json_bytes(sanitized)) > M4_MEMORY_MAX_BYTES:
        raise ValueError("M4 memory metadata exceeds the configured file size limit.")
    return sanitized


def _unique_warnings(warnings: list[WarningItem]) -> list[WarningItem]:
    result: list[WarningItem] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message, warning.detail)
        if key in seen:
            continue
        result.append(warning)
        seen.add(key)
    return result


def _memory_json_bytes(bundle: M4MemoryBundle) -> bytes:
    return json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2).encode("utf-8")


def _serialize_memory_bundle(bundle: M4MemoryBundle) -> bytes:
    payload = _memory_json_bytes(bundle)
    if len(payload) > M4_MEMORY_MAX_BYTES:
        raise ValueError("M4 memory payload exceeds the configured file size limit.")
    return payload


def _paper_claims(paper_card: dict[str, object]) -> list[tuple[str, object]]:
    fields = ["problem", "core_idea", "method_overview", "experiment_summary", "limitations", "background", "bottleneck"]
    return [(field, paper_card.get(field)) for field in fields if paper_card.get(field)]


def _conversation_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    history: list[dict[str, str]] = []
    for item in value[-12:]:
        if not isinstance(item, dict):
            continue
        role = _clean(item.get("role")).lower()
        if role not in {"user", "assistant"}:
            continue
        content = _compact_user_text(item.get("content"), max_chars=1200)
        if content:
            history.append({"role": role, "content": content})
    return history


def _llm_error_result(code: str, message: str, *, detail: str = "") -> dict[str, object]:
    return {"ok": False, "code": code, "message": message, "detail": detail}


def _evidence_text_by_ref(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for row in rows:
        ref = _clean(row.get("evidence_ref"))
        text = _clean(row.get("text"))
        if ref and text:
            grouped.setdefault(ref, []).append((_clean(row.get("source")), text))
    result: dict[str, list[str]] = {}
    for ref, candidates in grouped.items():
        primary = [
            text
            for source, text in candidates
            if not source.startswith("paper_card") and source != "paper_card"
        ]
        result[ref] = _unique(primary or [text for _source, text in candidates])
    return result


def _with_source_quote_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Give exact source rows stable IDs so the model need not recopy text.

    Audited paper-card wording is useful as a bilingual semantic bridge, but it
    is not the underlying source quotation. Only passage, claim, and formula
    evidence rows receive IDs that can satisfy the verbatim-quote gate.
    """

    result: list[dict[str, str]] = []
    source_index = 0
    for row in rows:
        item = dict(row)
        source = _clean(item.get("source"))
        if source and not source.startswith("paper_card") and source != "paper_card":
            source_index += 1
            item["quote_id"] = f"source_quote_{source_index:03d}"
        result.append(item)
    return result


def _source_quotes_by_id(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for row in rows:
        quote_id = _clean(row.get("quote_id"))
        ref = _clean(row.get("evidence_ref"))
        text = _clean(row.get("text"))
        if quote_id and ref and text:
            result[quote_id] = (ref, text)
    return result


def _claim_support_text_by_ref(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Add audited paper-card wording as a bilingual claim-validation bridge.

    Verbatim quotes are still checked only against ``_evidence_text_by_ref``,
    which prefers the underlying passage/claim evidence. The paper card may
    help match a Chinese explanation to English source evidence, but it cannot
    replace the required source quote.
    """

    result = _evidence_text_by_ref(rows)
    for row in rows:
        ref = _clean(row.get("evidence_ref"))
        text = _clean(row.get("text"))
        if ref and text:
            result[ref] = _unique([*result.get(ref, []), text])
    return result


def _validate_grounded_claim(
    value: object,
    *,
    allowed: set[str],
    evidence_by_ref: dict[str, list[str]],
    support_text_by_ref: dict[str, list[str]] | None = None,
    source_quotes_by_id: dict[str, tuple[str, str]] | None = None,
) -> tuple[GroundedClaim | None, str]:
    if not isinstance(value, dict):
        return None, "claim_not_object"
    text = _soften_mechanical_answer(
        _strip_internal_refs_from_answer(_normalize_answer_text(value.get("text"), max_chars=1200))
    )
    if not text:
        return None, "claim_text_missing"
    claim_type = _clean(value.get("claim_type")) or "paper_claim"
    if claim_type not in {"paper_claim", "explanation", "toy_example"}:
        return None, "claim_type_invalid"
    refs = _unique(_string_list(value.get("evidence_refs")))
    if not refs:
        return None, "claim_refs_missing"
    if any(ref not in allowed for ref in refs):
        return None, "claim_ref_not_allowed"
    if any(ref not in evidence_by_ref for ref in refs):
        return None, "claim_ref_has_no_evidence_text"

    raw_quotes = value.get("supporting_quotes", [])
    if not isinstance(raw_quotes, list):
        return None, "supporting_quotes_invalid"
    quoted_refs: set[str] = set()
    for raw_quote in raw_quotes:
        if not isinstance(raw_quote, dict):
            continue
        ref = _clean(raw_quote.get("evidence_ref"))
        quote_id = _clean(raw_quote.get("quote_id"))
        quote = _clean(raw_quote.get("quote"))
        if ref not in refs:
            continue
        source_quote = (source_quotes_by_id or {}).get(quote_id)
        if source_quote is not None and source_quote[0] == ref:
            quoted_refs.add(ref)
            continue
        if not quote:
            continue
        if _quote_matches_evidence(quote, evidence_by_ref.get(ref, [])):
            quoted_refs.add(ref)
    # Some providers still paraphrase or omit the requested quote_id. Resolve
    # that formatting error locally only when an exact server-held source row
    # exists for the ref and the claim independently passes the same audited
    # content gate for that ref. This avoids a second slow LLM call without
    # accepting the model's altered quotation as evidence.
    support_rows = support_text_by_ref or evidence_by_ref
    source_refs = {source_ref for source_ref, _text in (source_quotes_by_id or {}).values()}
    for ref in set(refs) - quoted_refs:
        ref_support = " ".join(support_rows.get(ref, evidence_by_ref.get(ref, [])))
        supported, _reason = _claim_content_supported(text, evidence_text=ref_support, claim_type=claim_type)
        if ref in source_refs and supported:
            quoted_refs.add(ref)
    if quoted_refs != set(refs):
        return None, "supporting_quote_not_verbatim"

    evidence_text = " ".join(text for ref in refs for text in support_rows.get(ref, evidence_by_ref[ref]))
    supported, reason = _claim_content_supported(text, evidence_text=evidence_text, claim_type=claim_type)
    if not supported:
        return None, reason
    return (
        GroundedClaim(
            text=text,
            evidence_refs=refs,
            claim_type=claim_type,
            support_status="SUPPORTED",
            uncertainty=_compact_user_text(value.get("uncertainty"), max_chars=300),
        ),
        "",
    )


def _quote_matches_evidence(quote: str, evidence_texts: list[str]) -> bool:
    compact_quote = _quote_key(quote)
    if len(compact_quote) < 12:
        return False
    return any(compact_quote in _quote_key(evidence) for evidence in evidence_texts)


def _quote_key(value: str) -> str:
    return re.sub(r"\s+", " ", _clean(value)).strip().casefold()


_GROUNDING_CONCEPTS: dict[str, tuple[str, ...]] = {
    "attention": ("attention", "注意力"),
    "evidence": ("evidence", "passage", "证据", "片段"),
    "retrieval": ("retrieval", "retrieve", "检索"),
    "sparse": ("sparse", "稀疏", "分散"),
    "connection": ("connect", "link", "aggregate", "连接", "聚合", "关联"),
    "architecture": ("architecture", "结构", "架构"),
    "weight": ("weight", "score", "权重", "分数", "打分"),
    "time_series": ("time series", "timeseries", "时间序列", "时序"),
    "anomaly": ("anomaly", "outlier", "异常"),
    "forecasting": ("forecast", "forecasting", "预测"),
    "imputation": ("imputation", "impute", "插补", "填补"),
    "graph": ("graph", "图结构", "图神经"),
    "gnn": ("gnn", "graph neural network", "图神经网络"),
    "diffusion": ("diffusion", "扩散模型"),
    "fourier": ("fourier", "fft", "傅里叶"),
    "spectral_residual": ("spectral residual", "谱残差"),
    "threshold": ("threshold", "阈值", "门限"),
    "convolution": ("convolution", "convolutional", "cnn", "卷积"),
    "transformer": ("transformer", "变换器"),
    "recurrent": ("lstm", "gru", "rnn", "recurrent", "循环神经"),
    "root_system": ("root system", "root architecture", "rsa", "根系", "根系结构"),
    "image_analysis": ("image", "imaging", "图像", "成像"),
    "segmentation": ("segment", "segmentation", "separate roots", "分割", "分离"),
    "phenotype_trait": ("trait", "phenotype", "性状", "表型"),
    "software_tool": ("software", "software tool", "软件", "工具"),
    "pipeline": ("pipeline", "workflow", "流水线", "工作流"),
    "reproducibility": ("reproduc", "可重复", "复现"),
    "user_interface": (
        "graphical user interface",
        "command line interface",
        "command-line interface",
        "gui",
        "图形用户界面",
        "命令行接口",
    ),
    "extensibility": ("extensible", "extend", "extension", "可扩展", "扩展"),
    "reconstruction_3d": ("3d reconstruction", "three-dimensional reconstruction", "3d重建", "三维重建"),
    "genotype": ("genotype", "基因型"),
    "rice": ("rice", "水稻"),
    "genetic": ("genetic", "heritable", "heritability", "遗传"),
    "growth_analysis": ("growth analysis", "time-lapse", "生长分析", "生长过程"),
    "dataset": ("dataset", "data set", "数据集"),
    "benchmark": ("benchmark", "基准"),
    "metric": ("metric", "f1", "auroc", "auc", "precision", "recall", "rmse", "mae", "mse", "指标", "准确率", "精确率", "召回率"),
    "comparison": ("outperform", "state-of-the-art", "sota", "优于", "超过基线", "提升", "最好", "最佳"),
}

_STRICT_GROUNDING_CONCEPTS = {
    "time_series",
    "anomaly",
    "forecasting",
    "imputation",
    "graph",
    "gnn",
    "diffusion",
    "fourier",
    "spectral_residual",
    "threshold",
    "convolution",
    "transformer",
    "recurrent",
    "root_system",
    "image_analysis",
    "segmentation",
    "phenotype_trait",
    "software_tool",
    "pipeline",
    "reproducibility",
    "user_interface",
    "extensibility",
    "reconstruction_3d",
    "genotype",
    "rice",
    "genetic",
    "growth_analysis",
    "dataset",
    "benchmark",
    "metric",
    "comparison",
}


_TRAIT_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "aspect ratio": ("aspect ratio", "长宽比"),
    "average width of roots": ("average width of roots", "average root width", "平均根宽", "根平均宽度"),
    "bushiness": ("bushiness", "灌木状", "丛生度", "茂密度"),
    "convex area": ("convex area", "凸面积", "凸包面积"),
    "network depth": ("network depth", "网络深度"),
    "network length distribution": ("network length distribution", "网络长度分布"),
    "major ellipse axis": ("major ellipse axis", "长轴", "椭圆长轴", "主椭圆轴"),
    "maximum number of roots": ("maximum number of roots", "最大根数", "最大根数量"),
    "maximum width of root system": ("maximum width of root system", "根系统最大宽度", "根系最大宽度"),
    "median number of roots": ("median number of roots", "中位数根数", "根数中位数"),
    "minimum ellipse axis": ("minimum ellipse axis", "短轴", "椭圆短轴", "最小椭圆轴"),
    "network area": ("network area", "网络面积"),
    "network length": ("network length", "网络长度"),
    "network solidity": ("network solidity", "网络坚固度", "网络实心度", "网络致密度"),
    "network surface area": ("network surface area", "网络表面积"),
    "network volume": ("network volume", "网络体积"),
    "network width to depth ratio": ("network width to depth ratio", "网络宽深比", "网络宽度深度比"),
    "perimeter": ("perimeter", "周长"),
    "specific root length": ("specific root length", "比根长"),
}


def _claim_content_supported(text: str, *, evidence_text: str, claim_type: str) -> tuple[bool, str]:
    claim_key = _grounding_key(text)
    evidence_key = _grounding_key(evidence_text)
    # Trait-list claims have a stricter domain-specific validator that checks
    # every named trait against bilingual aliases in the cited evidence. Run
    # it before generic wrapper concepts such as "software" or "root system".
    trait_list_support = _trait_list_claim_supported(text, evidence_text=evidence_text)
    if trait_list_support is not None:
        return trait_list_support
    claim_concepts = _grounding_concepts(claim_key)
    evidence_concepts = _grounding_concepts(evidence_key)
    missing_strict = (claim_concepts & _STRICT_GROUNDING_CONCEPTS) - evidence_concepts
    if missing_strict:
        return False, f"unsupported_specific_concept:{sorted(missing_strict)[0]}"

    if claim_type != "toy_example":
        claim_numbers = set(_grounded_numbers(text))
        evidence_numbers = set(_grounded_numbers(evidence_text))
        if claim_numbers - evidence_numbers:
            return False, "unsupported_number"
    dataset_names = _named_datasets_or_metrics(text)
    if any(_grounding_key(name) not in evidence_key for name in dataset_names):
        return False, "unsupported_dataset_or_metric"
    if _has_math_or_threshold_rule(text) and not _has_math_or_threshold_rule(evidence_text):
        return False, "unsupported_formula_or_threshold"

    matched_concepts = claim_concepts & evidence_concepts
    if claim_concepts:
        required = min(2, len(claim_concepts))
        if len(matched_concepts) < required:
            return False, "insufficient_concept_support"
        return True, ""

    claim_terms = _grounding_terms(text)
    evidence_terms = _grounding_terms(evidence_text)
    overlap = claim_terms & evidence_terms
    if len(overlap) >= 2 and len(overlap) / max(len(claim_terms), 1) >= 0.3:
        return True, ""
    return False, "insufficient_lexical_support"


def _trait_list_claim_supported(text: str, *, evidence_text: str) -> tuple[bool, str] | None:
    """Validate a translated trait list item by item against the source list."""

    match = re.search(r"(?:包括|如下|包含)\s*[:：]?\s*(.+?)(?:[。；;]|$)", text, flags=re.DOTALL)
    if match is None:
        return None
    raw_list = match.group(1).replace("以及", "、")
    raw_list = re.sub(r"(?<=\S)和(?=\S)", "、", raw_list)
    items = [item.strip(" \t\r\n、,，:：") for item in re.split(r"[、,，]", raw_list)]
    items = [item for item in items if item]
    if len(items) < 3:
        return None

    resolved_traits = [_canonical_trait_name(item) for item in items]
    # This validator is intentionally domain-scoped. Other papers can contain
    # perfectly valid non-RSA lists and must continue through the generic gate.
    if sum(bool(canonical) for canonical in resolved_traits) < 2:
        return None
    if any(not canonical for canonical in resolved_traits):
        return False, "unsupported_trait_item"
    claim_traits = [canonical for canonical in resolved_traits if canonical]
    if len(set(claim_traits)) != len(claim_traits):
        return False, "duplicate_trait_item"

    normalized_evidence = _normalized_trait_text(evidence_text)
    missing = [
        canonical
        for canonical in claim_traits
        if not any(
            _normalized_trait_text(alias) in normalized_evidence
            for alias in _TRAIT_NAME_ALIASES[canonical]
            if re.search(r"[a-z]", alias, flags=re.IGNORECASE)
        )
    ]
    if missing:
        return False, f"unsupported_trait_item:{missing[0]}"
    return True, ""


def _canonical_trait_name(value: str) -> str:
    normalized = _normalized_trait_text(value)
    for canonical, aliases in _TRAIT_NAME_ALIASES.items():
        for alias in aliases:
            normalized_alias = _normalized_trait_text(alias)
            if normalized == normalized_alias or normalized_alias in normalized:
                return canonical
    return ""


def _normalized_trait_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", _clean(value)).casefold()
    normalized = re.sub(r"(?<=\w)-\s+(?=\w)", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _grounding_key(value: str) -> str:
    return re.sub(r"\s+", " ", _clean(value).casefold()).strip()


def _grounding_concepts(value: str) -> set[str]:
    return {
        concept
        for concept, markers in _GROUNDING_CONCEPTS.items()
        if any(marker.casefold() in value for marker in markers)
    }


def _grounded_numbers(value: str) -> list[str]:
    return re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.])", value)


def _named_datasets_or_metrics(value: str) -> set[str]:
    names = set(
        re.findall(
            r"(?i)\b(?:NASA|SMD|MSL|SMAP|SWaT|WADI|PSM|NAB|UCR|Yahoo|F1|AUROC|AUC|RMSE|MAE|MSE)\b",
            value,
        )
    )
    names.update(
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_-]{2,})\s+(?:dataset|benchmark|metric)\b", value)
    )
    return names


def _has_math_or_threshold_rule(value: str) -> bool:
    normalized = _normalize_math_text(value)
    return bool(
        any(marker in normalized for marker in ["阈值", "threshold", "谱残差", "spectralresidual", "傅里叶", "fourier"])
        or re.search(r"(?:[=<>≤≥]|\\(?:frac|sum|sigma|mu)|[μστ])", value)
    )


def _grounding_terms(value: str) -> set[str]:
    lowered = _grounding_key(value)
    terms = {token for token in re.findall(r"[a-z][a-z0-9_-]{2,}", lowered) if token not in {"the", "and", "with", "this", "that", "from", "into"}}
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    for run in cjk_runs:
        terms.update(run[index : index + 2] for index in range(len(run) - 1))
    return terms


def _llm_failure_answer(*, code: str, message: str) -> str:
    return (
        "M4 这次没有拿到可用的大模型解释：返回内容未通过证据验证，因此没有改用本地卡片兜底，也没有展示未经校验的内容。\n\n"
        f"失败原因：{code}。{message}\n\n"
        "可以直接重试当前问题；若持续失败，请到设置页检查模型连接或切换模型。"
    )


def _run_async_llm(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if hasattr(coro, "close"):
        coro.close()
    raise RuntimeError("M4InteractionService cannot run async LLM calls inside an active event loop.")


def _m4_output_token_budget(llm_client: object) -> int:
    provider = getattr(llm_client, "provider", None)
    if str(getattr(provider, "kind", "") or "").strip().lower() == "anthropic_compatible":
        return 12_000
    return 3_200


def _claim_text(value: object) -> str:
    if isinstance(value, dict):
        return _usable_card_text(value.get("text") or value.get("plain"))
    return _usable_card_text(value)


def _usable_card_text(value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    compact = re.sub(r"[\s，。！？,.!?；;：:]+", "", text).lower()
    exact_placeholders = {
        "unknown",
        "insufficientevidence",
        "证据不足",
        "证据不足暂不展开",
        "暂无足够证据",
        "暂无证据",
        "未提供",
        "未知",
    }
    if compact in exact_placeholders:
        return ""
    fallback_patterns = (
        r"^论文把.+概括为主要研究问题[。.]?$",
        r"^核心想法围绕.+形成方法改进[。.]?$",
        r"^方法围绕.+展开建模流程[。.]?$",
        r"^实验摘要保留.+相关证据信号[。.]?$",
    )
    if any(re.match(pattern, text, flags=re.IGNORECASE) for pattern in fallback_patterns):
        return ""
    return text


def _is_placeholder_selection(value: object) -> bool:
    text = _clean(value)
    return bool(text) and not _usable_card_text(text)


def _formula_card_is_usable(formula: dict[str, object]) -> bool:
    origin = _clean(formula.get("origin") or formula.get("formula_origin")).lower()
    coverage = _clean(formula.get("coverage_status")).upper()
    derivation = _clean(formula.get("derivation_status")).upper()
    evidence_status = _clean(formula.get("evidence_status") or formula.get("status")).upper()
    warnings = " ".join(_string_list(formula.get("warnings"))).upper()
    if origin == "raw_formula_text":
        return False
    if coverage.startswith("BLOCKED") or derivation.startswith("BLOCKED"):
        return False
    if evidence_status in {"INSUFFICIENT_EVIDENCE", "BLOCKED", "REJECTED"}:
        return False
    if "RAW_FORMULA_TEXT" in warnings:
        return False
    return bool(_clean(formula.get("evidence_ref")))


def _is_unreliable_evidence_candidate(candidate: dict[str, object]) -> bool:
    origins = {item.lower() for item in _string_list(candidate.get("formula_origins"))}
    risks = {item.upper() for item in _string_list(candidate.get("risk_flags"))}
    return "raw_formula_text" in origins or "RAW_FORMULA_TEXT" in risks


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


def _clarifying_question_answer(question: str, paper_card: dict[str, object]) -> str:
    question_hint = _compact_user_text(question, max_chars=80) or "这个问题"
    method = _teach_phrase(_claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea")))
    problem = _teach_phrase(_claim_text(paper_card.get("problem")))
    choices = _clarifying_follow_ups(paper_card)
    anchor = ""
    if method:
        anchor = f"我看当前论文里最容易先讲的是方法这块：{method}"
    elif problem:
        anchor = f"我看当前论文里最容易先讲的是它要解决的困难：{problem}"
    else:
        anchor = "我可以先围绕论文的问题、方法、证据或公式来讲。"
    return (
        f"我先追问一下：你说的“{question_hint}”是想问哪一块？"
        f"\n\n{anchor}"
        "\n\n你可以直接回我其中一种："
        f"\n1. {choices[0]}"
        f"\n2. {choices[1]}"
        f"\n3. {choices[2]}"
        "\n\n如果你只是想让我先讲，我会默认从“方法为什么能解决问题”开始讲。"
    )


def _clarifying_follow_ups(paper_card: dict[str, object]) -> list[str]:
    method = _teach_phrase(_claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea")))
    if method:
        method_question = "你先讲这个方法到底怎么起作用。"
    else:
        method_question = "你先讲论文的核心方法。"
    return [
        method_question,
        "我想看它对应哪几条证据。",
        "我想问公式、变量或理论假设是什么意思。",
    ]


def _selection_followup_answer(*, question: str, selected_text: str, claim_text: str, section: str) -> str:
    label = _user_facing_section_label(section)
    question_hint = _compact_user_text(question, max_chars=90)
    taught_claim = _teach_phrase(claim_text, max_chars=180)
    if _is_why_question(question):
        return (
            f"它重要在于：这段证据不是孤立描述，而是在“{label}”里说明“{taught_claim}”。"
            "换句话说，它把论文想解决的困难和论文采用的机制接到了一起；读理论时先抓这条连接，比只背术语更容易懂。"
        )
    if _is_evidence_question(question):
        return (
            f"这段可以作为回答“{question_hint}”的正文依据：它来自“{label}”，"
            f"支撑的论断是“{taught_claim}”。"
        )
    return (
        f"结合你的追问“{question_hint}”，可以把这段当作“{label}”证据来读："
        f"它支撑的是“{taught_claim}”，回答时应围绕这个论断展开。"
    )


def _missing_limitation_answer(
    paper_card: dict[str, object],
    *,
    question: str,
    evidence_rows: list[dict[str, object]] | None = None,
) -> str:
    rows = _paper_card_claim_rows(paper_card)
    parts = [
        f"这个问题要谨慎一点：你问的是“{_compact_user_text(question, max_chars=90)}”，但当前论文卡片没有给出可追踪的局限证据，所以这里不能硬编局限。",
    ]
    method = _claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea"))
    experiment = _claim_text(paper_card.get("experiment_summary"))
    if method:
        parts.append(f"现在能确认的是方法怎么做：{_teach_phrase(method)}")
    if experiment:
        parts.append(f"实验材料里能看到的是：{_teach_phrase(experiment)}")
    focused = []
    seen: set[str] = set()
    for candidate in evidence_rows or []:
        rendered = _candidate_user_facing_evidence(candidate)
        key = _normalize(rendered)
        if rendered and key not in seen:
            focused.append(rendered)
            seen.add(key)
    if focused:
        parts.append("也就是说，能追到的证据边界只有这些：" + "；".join(focused[:3]))
    elif rows:
        parts.append("也就是说，能追到的证据边界只有这些：" + "；".join(f"{label}：{_teach_phrase(text)}" for label, text, _ref in rows[:3]))
    parts.append("更稳妥的回答是：这篇论文当前材料支持它的方法和实验设置，但没有足够依据判断具体局限。")
    return "\n\n".join(parts)


def _structured_paper_answer(
    paper_card: dict[str, object],
    *,
    focus: str = "",
    question: str = "",
    evidence_rows: list[dict[str, object]] | None = None,
) -> str:
    rows = _paper_card_claim_rows(paper_card)
    if not rows:
        summary = _usable_card_text(paper_card.get("one_sentence_summary")) or _usable_card_text(
            paper_card.get("thirty_second")
        )
        return f"我先按论文整体来讲：{_teach_phrase(summary)}" if summary else ""
    by_label = {label: text for label, text, _ref in rows}
    problem = _teach_phrase(by_label.get("研究问题", ""))
    idea = _teach_phrase(by_label.get("核心想法", ""))
    method = _teach_phrase(by_label.get("方法机制", ""))
    experiment = _teach_phrase(by_label.get("实验结论", ""))
    limitations = _teach_phrase(by_label.get("局限", ""))
    summary = _teach_phrase(
        _usable_card_text(paper_card.get("one_sentence_summary"))
        or _usable_card_text(paper_card.get("thirty_second"))
    )

    focus_text = method or idea or summary or problem
    if focus == "实验结论" and experiment:
        focus_text = experiment
    elif focus == "研究问题" and problem:
        focus_text = problem
    elif focus == "核心想法" and idea:
        focus_text = idea
    elif focus == "局限" and limitations:
        focus_text = limitations

    if question:
        parts = [f"我先按“{_compact_user_text(question, max_chars=90)}”来理解：这篇论文的抓手是{focus_text}"]
    else:
        parts = [f"这篇论文的抓手是{focus_text}"]
    if problem:
        parts.append(f"它先遇到的困难是{problem}")
    if idea or method:
        mechanism = _join_distinct_phrases([idea, method])
        parts.append(f"做法上，{mechanism}。")
    why_items = []
    if problem and method:
        why_items.append(
            f"它不是只重复论文目标，而是把“{_strip_terminal_punctuation(method)}”作为具体步骤，"
            f"用来回应“{_strip_terminal_punctuation(problem)}”这个困难"
        )
    elif method:
        why_items.append("它把论文的方法主张落到可执行的建模步骤上")
    if experiment:
        why_items.append(f"实验结论显示：{experiment}")
    if limitations:
        why_items.append(f"同时要注意局限：{limitations}")
    if why_items:
        parts.append(f"这一步之所以有用，是因为{'；'.join(why_items)}")
    evidence_lines = [f"{label}来自论文卡片中的正文依据：{_teach_phrase(text)}" for label, text, _ref in rows[:4]]
    focused_evidence: list[str] = []
    seen_focused_evidence: set[str] = set()
    seen_focused_bodies: set[str] = set()
    for candidate in evidence_rows or []:
        rendered = _candidate_user_facing_evidence(candidate)
        key = _normalize(rendered)
        body_key = _evidence_line_body_key(rendered)
        if rendered and key not in seen_focused_evidence and not _has_redundant_body(body_key, seen_focused_bodies):
            focused_evidence.append(rendered)
            seen_focused_evidence.add(key)
            seen_focused_bodies.add(body_key)
    if focused_evidence:
        parts.append("贴着你的问题看，可以追到这些依据：" + "；".join(focused_evidence[:3]))
    if evidence_lines:
        parts.append("更完整的证据边界是：" + "；".join(evidence_lines))
    return "\n\n".join(parts)


def _problem_solution_answer(
    paper_card: dict[str, object],
    *,
    question: str,
    evidence_rows: list[dict[str, object]] | None = None,
) -> str:
    problem = _teach_phrase(_claim_text(paper_card.get("problem")))
    idea = _teach_phrase(_claim_text(paper_card.get("core_idea")))
    method = _teach_phrase(_claim_text(paper_card.get("method_overview")))
    experiment = _teach_phrase(_claim_text(paper_card.get("experiment_summary")))
    summary = _teach_phrase(
        _usable_card_text(paper_card.get("one_sentence_summary"))
        or _usable_card_text(paper_card.get("thirty_second"))
    )
    if not any([problem, idea, method, summary]):
        return ""

    lead_target = problem or summary
    parts = [f"它解决的不是一个泛泛的“效果提升”问题，而是：{lead_target}"]
    if method:
        parts.append(f"它的解法可以抓成一条线：{method}")
    elif idea:
        parts.append(f"它的核心想法是：{idea}")
    if problem and (method or idea):
        mechanism = method or idea
        parts.append(
            f"这条线能回应问题，是因为它把“{_strip_terminal_punctuation(problem)}”"
            f"转成了“{_strip_terminal_punctuation(mechanism)}”这样可执行的步骤。"
        )
    if experiment:
        parts.append(f"论文给出的效果依据是：{experiment}")
    focused = _focused_evidence_lines(evidence_rows)
    if focused:
        parts.append("能追到的正文依据包括：" + "；".join(focused[:2]))
    return "\n\n".join(parts)


def _example_driven_paper_answer(
    paper_card: dict[str, object],
    *,
    question: str,
    evidence_rows: list[dict[str, object]] | None = None,
) -> str:
    problem = _teach_phrase(_claim_text(paper_card.get("problem")))
    method = _teach_phrase(
        _claim_text(paper_card.get("method_overview")) or _claim_text(paper_card.get("core_idea"))
    )
    parts: list[str] = []
    if problem:
        parts.append(f"可以把论文卡片里的困难放进一个简化场景：{problem}")
    if method:
        parts.append(f"在这个场景中，只能沿用论文卡片明确写出的处理步骤：{method}")
    parts.append(
        "这里不自行添加具体数值、阈值或额外算法步骤。若要做数值玩具例子，必须先逐项核对对应公式卡片和证据。"
    )
    focused = _focused_evidence_lines(evidence_rows)
    if focused:
        parts.append("对应到正文证据，能看到：" + "；".join(focused[:2]))
    return "\n\n".join(parts)


def _focused_evidence_lines(evidence_rows: list[dict[str, object]] | None) -> list[str]:
    focused: list[str] = []
    seen: set[str] = set()
    for candidate in evidence_rows or []:
        rendered = _candidate_user_facing_evidence(candidate)
        key = _normalize(rendered)
        if rendered and key not in seen:
            focused.append(rendered)
            seen.add(key)
    return focused


def _formula_context_text(formula: dict[str, object]) -> str:
    purpose = _teach_phrase(_clean(formula.get("purpose")) or _clean(formula.get("plain_summary")))
    intuition = _teach_phrase(_clean(formula.get("intuition")))
    example = _teach_phrase(_clean(formula.get("numeric_example")))
    removed = _teach_phrase(_clean(formula.get("what_if_removed")) or _clean(formula.get("remove_effect")))
    sensitivity = _teach_phrase(_clean(formula.get("weight_sensitivity")) or _clean(formula.get("weight_change_effect")))
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
    purpose = _teach_phrase(_clean(formula.get("purpose")) or _clean(formula.get("plain_summary")))
    symbols = _formula_symbol_summary(formula)
    terms = _formula_term_summary(formula)
    intuition = _teach_phrase(_clean(formula.get("intuition")) or _clean(formula.get("plain_summary")))
    example = _teach_phrase(_clean(formula.get("numeric_example")))
    removed = _teach_phrase(_clean(formula.get("what_if_removed")) or _clean(formula.get("remove_effect")))
    sensitivity = _teach_phrase(_clean(formula.get("weight_sensitivity")) or _clean(formula.get("weight_change_effect")))

    parts = [f"这条公式卡片记录的目标是：{purpose}"] if purpose else []
    if symbols:
        parts.append(f"公式卡片明确记录的对象是：{symbols}")
    if terms:
        parts.append(f"如果拆开关键项，可以这样看：{terms}")
    if intuition and intuition != purpose:
        parts.append(f"为什么要这样做呢？{intuition}")
    if example:
        parts.append(f"例子：{example}")
    if removed:
        parts.append(f"拿掉影响：{removed}")
    if sensitivity:
        parts.append(f"权重变化：{sensitivity}")
    return "\n\n".join(parts) or "当前公式卡片没有足够的可展示解释。"


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
            rendered.append(f"{symbol} 表示：{_teach_phrase(meaning)}")
        elif meaning:
            rendered.append(_teach_phrase(meaning))
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
            _teach_phrase(_clean(item.get("meaning"))),
            f"鼓励 {_teach_phrase(_clean(item.get('encourages')))}" if _clean(item.get("encourages")) else "",
            f"惩罚 {_teach_phrase(_clean(item.get('penalizes')))}" if _clean(item.get("penalizes")) else "",
            f"去掉后 {_teach_phrase(_clean(item.get('if_removed')))}" if _clean(item.get("if_removed")) else "",
        ]
        detail_text = "，".join(detail for detail in details if detail)
        if term and detail_text:
            rendered.append(f"{term}：{detail_text}")
        elif detail_text:
            rendered.append(detail_text)
        if len(rendered) >= 8:
            break
    return "；".join(rendered)


def _advisor_expected_points_from_claims(*, problem: str, method: str, core_idea: str) -> list[str]:
    points = []
    if problem:
        points.append(f"先说清楚论文真正卡住的地方是“{problem}”。")
    if method:
        points.append(f"讲方法时别只复述名称，要说明“{method}”到底怎样发挥作用。")
    elif core_idea:
        points.append(f"讲核心想法时别只复述名称，要说明“{core_idea}”到底怎样发挥作用。")
    if core_idea and core_idea != method:
        points.append(f"把核心想法“{core_idea}”和方法之间的关系讲顺。")
    points.append("最后补一句论文中哪类依据支持这个判断，例如正文方法描述、实验结果或局限分析。")
    return points


def _advisor_point_coverage(*, answer: str, expected_points: list[str]) -> tuple[list[str], list[str]]:
    if not answer:
        return [], expected_points
    answer_terms = _advisor_terms(answer)
    covered: list[str] = []
    missing: list[str] = []
    for point in expected_points:
        category = _advisor_point_category(point)
        point_terms = _advisor_terms(point)
        overlap = len(answer_terms & point_terms)
        has_category_signal = bool(answer_terms & _advisor_category_terms(category))
        min_overlap = 2 if category in {"problem", "mechanism"} else 1
        if has_category_signal or overlap >= min_overlap:
            covered.append(point)
        else:
            missing.append(point)
    return covered, missing


def _advisor_score(*, answer: str, covered_count: int, total_count: int) -> float:
    if not answer:
        return 0.0
    coverage = covered_count / max(total_count, 1)
    detail_bonus = 0.08 if len(answer) >= 80 else (0.03 if len(answer) >= 40 else 0.0)
    structure_bonus = 0.07 if any(marker in answer for marker in ["问题", "机制", "证据", "实验", "because", "therefore"]) else 0.0
    return min(1.0, max(0.0, coverage * 0.85 + detail_bonus + structure_bonus))


def _advisor_misconceptions(answer: str) -> list[str]:
    if not answer:
        return ["还没有作答。"]
    text = answer.lower()
    misconceptions: list[str] = []
    if len(answer) < 24:
        misconceptions.append("回答太短，像关键词列表，还没有形成可复述的组会回答。")
    if any(marker in text for marker in ["随便", "万能", "肯定有效", "because it is ai", "because it uses ai"]):
        misconceptions.append("回答里有泛化判断，建议换成论文证据能支撑的具体机制。")
    return misconceptions


def _advisor_improvement_steps(missing_points: list[str]) -> list[str]:
    if not missing_points:
        return ["把现在这版压缩成 2-3 句：先问题，再机制，最后证据。"]
    steps: list[str] = []
    for point in missing_points[:3]:
        category = _advisor_point_category(point)
        if category == "problem":
            steps.append("先补论文痛点：旧方法或当前任务到底卡在哪里。")
        elif category == "mechanism":
            steps.append("再补方法机制：这个结构或步骤具体怎样缓解痛点。")
        elif category == "evidence":
            steps.append("最后补证据类型：正文方法描述、实验结果或局限分析支持了哪一句判断。")
        else:
            steps.append("把缺失要点和前一句回答接起来，形成连续解释。")
    return _unique(steps)


def _advisor_feedback(*, answer: str, score: float, covered: list[str], missing: list[str]) -> str:
    if not answer:
        return "还没有看到你的回答。先用三句话试一版：论文问题是什么，方法怎么解决，哪类证据支持这个判断。"
    covered_labels = "、".join(_advisor_point_label(point) for point in covered) or "暂时还不明显"
    missing_labels = "、".join(_advisor_point_label(point) for point in missing) or "没有明显缺口"
    if score >= 0.75:
        lead = "这版已经像组会回答了：有主线，也能看出你在把方法和证据连起来。"
    elif score >= 0.45:
        lead = "方向是对的，但还需要把缺口补实，避免听起来像只背了方法名。"
    else:
        lead = "这版还偏散，建议先按“问题-机制-证据”重组。"
    return f"{lead}\n\n已经覆盖：{covered_labels}。\n还要补：{missing_labels}。"


def _advisor_next_question(missing_points: list[str]) -> str:
    if not missing_points:
        return "如果把你的回答再压缩到 20 秒，你会保留哪一句作为核心机制？"
    category = _advisor_point_category(missing_points[0])
    if category == "problem":
        return "请先补一句：论文要解决的具体痛点是什么，为什么旧做法不够？"
    if category == "mechanism":
        return "请补一句：这个方法的关键机制怎样作用到刚才那个痛点上？"
    if category == "evidence":
        return "请补一句：论文中哪类证据支持这个机制，正文描述还是实验结果？"
    return "请把缺失要点补成一句能直接放进组会回答里的话。"


def _advisor_point_category(point: str) -> str:
    text = point.lower()
    if text.startswith("问题") or "problem" in text or "痛点" in text:
        return "problem"
    if text.startswith("机制") or text.startswith("连接") or "method" in text or "mechanism" in text or "方法" in text:
        return "mechanism"
    if text.startswith("证据") or "evidence" in text or "实验" in text:
        return "evidence"
    return "other"


def _advisor_point_label(point: str) -> str:
    category = _advisor_point_category(point)
    return {
        "problem": "问题背景",
        "mechanism": "方法机制",
        "evidence": "证据支撑",
    }.get(category, _compact_user_text(point, max_chars=24))


def _advisor_category_terms(category: str) -> set[str]:
    groups = {
        "problem": {"问题", "痛点", "难点", "挑战", "瓶颈", "解决", "problem", "challenge", "brittle", "sparse", "retrieval"},
        "mechanism": {"方法", "机制", "结构", "步骤", "连接", "建模", "attention", "architecture", "method", "mechanism", "connect", "link", "model"},
        "evidence": {"证据", "依据", "论文", "正文", "实验", "结果", "显示", "benchmark", "evidence", "experiment", "result", "paper"},
    }
    return groups.get(category, set())


def _advisor_terms(value: str) -> set[str]:
    text = value.lower()
    terms = {token for token in re.findall(r"[a-z0-9][a-z0-9_-]+", text) if len(token) > 2}
    cjk = re.findall(r"[\u4e00-\u9fff]", value)
    terms.update(cjk)
    terms.update("".join(cjk[index : index + 2]) for index in range(max(0, len(cjk) - 1)))
    terms.update(marker for marker in ["问题", "痛点", "机制", "方法", "证据", "实验", "结果", "论文"] if marker in value)
    return terms


def _warning(code: str, message: str, *, detail: str = "") -> WarningItem:
    return WarningItem(code=code, message=message, detail=detail)


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


def _soften_mechanical_answer(value: str) -> str:
    text = value
    replacements = [
        (r"(?m)^重点[:：]\s*", "我先抓最核心的点："),
        (r"(?m)^问题[:：]\s*", "它先遇到的困难是："),
        (r"(?m)^核心机制[:：]\s*", "做法上，"),
        (r"(?m)^为什么有效[:：]\s*", "这一步有用，是因为："),
        (r"(?m)^对应证据[:：]\s*", "能追到的依据是："),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text.strip()


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


def _should_reject_llm_answer_for_question(
    question: str,
    answer: str,
    *,
    context: dict[str, object] | None = None,
) -> bool:
    if _looks_like_mojibake_answer(answer):
        return True
    if _uses_unsupported_external_threshold_rule(answer, context=context):
        return True
    if _question_wants_example(question) and not _answer_has_concrete_example(answer):
        return True
    if _is_problem_solution_question(question) and _answer_too_abstract_for_problem(answer):
        return True
    if _requires_explicit_problem_statement(question) and not _answer_addresses_research_problem(answer):
        return True
    return False


def _should_include_formula_context(question: str, selected_text: str) -> bool:
    text = f"{question} {selected_text}".lower()
    compact = re.sub(r"\s+", "", text)
    return (
        _question_wants_example(text)
        or _is_formula_question(question, selected_text)
        or any(marker in compact for marker in ["公式", "阈值", "变量", "机制", "方法", "怎么算", "如何判断", "example", "threshold"])
    )


def _uses_unsupported_external_threshold_rule(
    answer: str,
    *,
    context: dict[str, object] | None = None,
) -> bool:
    answer_text = _normalize_math_text(answer)
    if not _has_external_threshold_marker(answer_text):
        return False
    context_text = _normalize_math_text(json.dumps(context or {}, ensure_ascii=False))
    return not _has_external_threshold_marker(context_text)


def _has_external_threshold_marker(text: str) -> bool:
    markers = [
        "μ+3σ",
        "mean+3标准差",
        "均值加3倍标准差",
        "平均值加3倍标准差",
        "三倍标准差",
        "3σ",
    ]
    if any(marker in text for marker in markers):
        return True
    return bool(re.search(r"(?:μ|mu|mean|均值|平均值).{0,8}3(?:倍)?.{0,4}(?:σ|标准差)", text))


def _normalize_math_text(value: object) -> str:
    text = _clean(value).lower()
    replacements = {
        "µ": "μ",
        "mu": "μ",
        "sigma": "σ",
        "\\sigma": "σ",
        "std": "标准差",
        "standarddeviation": "标准差",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"[\s_{}()（）\\]+", "", text)


def _question_wants_example(question: str) -> bool:
    text = question.lower()
    return any(marker in text for marker in ["举例", "例子", "示例", "详细说明", "具体说明", "example", "concrete"])


def _answer_has_concrete_example(answer: str) -> bool:
    text = _clean(answer)
    if not any(marker in text for marker in ["例如", "比如", "假设", "举个", "例子", "输入", "输出", "序列"]):
        return False
    has_number_or_formula_step = bool(re.search(r"\d|=|>|<|\[[^\]]+\]", text))
    has_step_marker = any(marker in text for marker in ["第一", "先", "再", "最后", "步骤", "得到", "输出"])
    return has_number_or_formula_step and has_step_marker


def _is_problem_solution_question(question: str) -> bool:
    text = question.lower()
    compact = re.sub(r"\s+", "", text)
    return any(marker in compact for marker in ["解决什么问题", "解决了什么问题", "问题是什么", "要解决什么", "solve", "problem"])


def _answer_too_abstract_for_problem(answer: str) -> bool:
    text = _clean(answer)
    # Claims reaching this point already passed verbatim-quote and content-level
    # evidence checks. A long, domain-specific keyword allow-list rejects valid
    # concise answers for systems/database papers while adding no grounding.
    return len(text) < 40


def _answer_addresses_research_problem(answer: str) -> bool:
    text = _clean(answer).lower()
    markers = (
        "问题",
        "困难",
        "痛点",
        "挑战",
        "不足",
        "局限",
        "难以",
        "无法",
        "耗时",
        "误差",
        "错误",
        "重叠",
        "缺少",
        "需要",
        "瓶颈",
        "problem",
        "challenge",
        "limitation",
        "difficulty",
        "time-consuming",
        "time consuming",
        "error",
        "overlap",
        "hamper",
        "need for",
    )
    return any(marker in text for marker in markers)


def _answer_aligned_with_selection(answer: str, selected_text: str) -> bool:
    selected = _usable_card_text(selected_text)
    if not selected:
        return False
    answer_lower = _clean(answer).lower()
    selected_lower = selected.lower()
    if _normalize(selected) and _normalize(selected) in _normalize(answer):
        return True

    latin_anchors = {
        token
        for token in re.findall(r"[a-z][a-z0-9_-]{3,}", selected_lower)
        if token not in {"this", "that", "with", "from", "method", "image", "analysis"}
    }
    if any(anchor in answer_lower for anchor in latin_anchors):
        return True

    concept_groups = (
        (("image-analysis", "image analysis"), ("图像分析",)),
        (("attention architecture",), ("注意力架构", "注意力结构")),
        (("root system", "root architecture"), ("根系", "根结构")),
        (("smartroot",), ("smartroot",)),
    )
    for source_terms, answer_terms in concept_groups:
        if any(term in selected_lower for term in source_terms) and any(term in answer_lower for term in answer_terms):
            return True

    selected_cjk = "".join(re.findall(r"[\u4e00-\u9fff]", selected))
    ignored = {"核心", "想法", "方法", "形成", "改进", "这段", "内容", "论文"}
    anchors = {
        selected_cjk[index : index + 2]
        for index in range(max(0, len(selected_cjk) - 1))
        if selected_cjk[index : index + 2] not in ignored
    }
    if anchors and any(anchor in answer for anchor in anchors):
        return True

    # Very short or generic selections do not provide a stable lexical anchor;
    # their grounding is enforced by the selected evidence reference instead.
    return len(_normalize(selected)) < 8 or not (latin_anchors or anchors)


def _requires_explicit_problem_statement(question: str) -> bool:
    text = _clean(question).lower()
    compact = re.sub(r"\s+", "", text)
    return "真正" in compact or "什么问题" in compact or "痛点" in compact or "research problem" in text


def _looks_like_mojibake_answer(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    markers = [chr(codepoint) for codepoint in (0x6D93, 0x9359, 0x93B4, 0x951B, 0x7ECB, 0x9225, 0x20AC)]
    markers.append(chr(0x4FD3) + "n")
    hit_count = sum(text.count(marker) for marker in markers)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return hit_count >= 4 and hit_count > max(3, chinese_chars // 12)


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


def _is_non_paper_question(question: str) -> bool:
    text = question.lower()
    compact = re.sub(r"[\s，。！？,.!?；;：:\"'“”‘’、]+", "", text)
    if not compact:
        return False
    if _is_general_chat_question(question):
        return True

    hard_off_topic_markers = [
        "天气",
        "几点",
        "日期",
        "今天几号",
        "星期几",
        "讲笑话",
        "讲个笑话",
        "说笑话",
        "笑话",
        "写诗",
        "写首诗",
        "讲故事",
        "写故事",
        "歌词",
        "菜谱",
        "做饭",
        "订机票",
        "订票",
        "订酒店",
        "简历",
        "求职信",
        "weather",
        "time is it",
        "what time",
        "date today",
        "joke",
        "poem",
        "story",
        "lyrics",
        "recipe",
        "cook",
        "flight",
        "hotel",
        "ticket",
        "resume",
        "cover letter",
    ]
    if any(marker in text for marker in hard_off_topic_markers):
        return True

    has_paper_intent = _has_paper_intent(question)
    code_request_markers = ["写代码", "编代码", "write code"]
    if any(marker in text for marker in code_request_markers):
        return True
    programming_terms = ["python", "javascript", "typescript", "sql"]
    programming_actions = [
        "帮我写",
        "写一段",
        "写一个",
        "生成",
        "实现",
        "write",
        "create",
        "generate",
        "implement",
        "code",
    ]
    if any(term in text for term in programming_terms) and any(action in text for action in programming_actions):
        return True

    if has_paper_intent:
        return False

    if any(term in text for term in programming_terms):
        return True

    off_topic_task_markers = [
        "帮我写",
        "帮我生成",
        "帮我创作",
        "生成一段",
        "写一段",
        "写一个",
        "创作",
        "draft",
        "write a",
        "write an",
        "create a",
        "generate a",
    ]
    return any(marker in text for marker in off_topic_task_markers)


def _has_paper_intent(question: str) -> bool:
    text = question.lower()
    return any(
        marker in text
        for marker in [
            "论文",
            "这篇",
            "文中",
            "文章",
            "paper",
            "method",
            "formula",
            "equation",
            "symbol",
            "evidence",
            "experiment",
            "result",
            "limitation",
            "contribution",
            "abstract",
            "section",
            "claim",
            "方法",
            "公式",
            "变量",
            "符号",
            "证据",
            "实验",
            "结果",
            "局限",
            "贡献",
            "摘要",
            "章节",
            "模型",
            "算法",
            "定理",
            "证明",
        ]
    )


def _is_underspecified_question(question: str) -> bool:
    text = re.sub(r"[\s，。！？,.!?]+", "", question.lower())
    if not text:
        return False
    if _is_general_chat_question(question):
        return False
    vague_exact = {
        "这个呢",
        "这个",
        "这个怎么说",
        "这个怎么讲",
        "这个怎么看",
        "这个怎么理解",
        "讲一下",
        "讲讲",
        "说一下",
        "怎么看",
        "不懂",
        "没看懂",
        "看不懂",
        "啥意思",
        "什么意思",
        "为什么",
        "怎么回事",
    }
    if text in vague_exact:
        return True
    if len(text) <= 12 and any(marker in text for marker in ["这个", "这块", "这里", "它", "为什么", "怎么", "讲一下", "不懂"]):
        specific_markers = ["方法", "公式", "变量", "证据", "实验", "结果", "局限", "贡献", "问题", "理论", "假设"]
        return not any(marker in text for marker in specific_markers)
    return False


def _has_followup_reference(question: str) -> bool:
    text = re.sub(r"\s+", "", question.lower())
    return any(
        marker in text
        for marker in [
            "它",
            "这个",
            "这种",
            "上述",
            "前面",
            "刚才",
            "那为什么",
            "那怎么",
            "那它",
            "继续",
            "展开讲",
            "再具体",
            "和前者",
            "与前者",
        ]
    )


def _is_evidence_question(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ["证据", "evidence", "对应哪", "引用"])


def _is_why_question(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ["为什么", "为何", "怎么", "如何", "why", "how", "important", "重要"])


def _is_limitation_question(question: str) -> bool:
    text = question.lower()
    return any(term in text for term in ["局限", "不足", "缺点", "弱点", "限制", "limitation", "weakness", "drawback"])


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


def _candidate_text(candidate: dict[str, object]) -> str:
    return " ".join(
        _clean(candidate.get(key))
        for key in ("claim_text", "quote_or_summary", "source_sentence", "text", "section", "claim_type")
        if _clean(candidate.get(key))
    )


def _candidate_user_facing_evidence(candidate: dict[str, object]) -> str:
    if _is_front_matter_candidate(candidate):
        return ""
    section = _user_facing_section_label(_clean(candidate.get("section")) or "正文")
    text = (
        _clean(candidate.get("claim_text"))
        or _clean(candidate.get("quote_or_summary"))
        or _clean(candidate.get("source_sentence"))
        or _clean(candidate.get("text"))
    )
    if not text:
        return ""
    return f"{section}：{_teach_phrase(text, max_chars=220)}"


def _evidence_line_body_key(line: str) -> str:
    body = re.sub(r"^[^：:]{1,16}[：:]", "", line)
    return _normalize(body)


def _has_redundant_body(body_key: str, seen_bodies: set[str]) -> bool:
    if not body_key:
        return False
    for seen in seen_bodies:
        if not seen:
            continue
        shorter, longer = sorted([body_key, seen], key=len)
        if len(shorter) >= 18 and shorter in longer:
            return True
    return False


def _strip_terminal_punctuation(value: str) -> str:
    return re.sub(r"[。.!！?？]+$", "", _clean(value))


def _join_distinct_phrases(values: list[str]) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        phrase = _strip_terminal_punctuation(value)
        if not phrase:
            continue
        key = _normalize(phrase)
        if key in seen or _has_redundant_body(key, seen):
            continue
        result.append(phrase)
        seen.add(key)
    return "；".join(result)


def _user_facing_section_label(section: str) -> str:
    normalized = _clean(section).lower()
    mapping = {
        "method": "方法",
        "method_overview": "方法机制",
        "problem": "研究问题",
        "core_idea": "核心想法",
        "experiment_summary": "实验结论",
        "limitations": "局限",
        "background": "背景",
        "bottleneck": "瓶颈",
        "result": "实验结果",
        "results": "实验结果",
        "discussion": "讨论",
        "正文": "正文",
    }
    return mapping.get(normalized, section or "正文")


def _teach_phrase(value: str, *, max_chars: int = 260) -> str:
    text = _compact_user_text(value, max_chars=max_chars)
    if not text:
        return ""
    exact = {
        "Scores each evidence passage with an attention weight.": "给每个证据片段分配一个注意力权重，也就是让模型判断哪段证据更值得关注。",
        "x is transformed into an attention score.": "x 会被转换成注意力分数，用来表示这段证据在当前问题里有多重要。",
        "the evidence passage representation": "证据片段的向量表示，也就是模型内部用来描述这段证据的一组特征。",
        "The attention architecture links sparse evidence passages to solve the retrieval problem.": "注意力架构把分散、稀疏的证据片段连接起来，用来缓解检索时证据不完整、不稳定的问题。",
        "The attention architecture links sparse evidence passages.": "注意力架构会把分散的证据片段连接起来。",
        "Sparse evidence passages make retrieval brittle.": "证据片段太分散，会让检索结果不稳定、容易漏掉关键信息。",
        "Use attention to connect related evidence passages.": "用注意力机制把相关证据片段连接起来，让模型看到片段之间的关系。",
        "An attention architecture links sparse evidence passages.": "用注意力架构连接分散的证据片段。",
        "The method is evaluated on retrieval benchmarks.": "论文在检索基准上评估了这个方法。",
        "A paper about attention architecture for evidence retrieval.": "这篇论文研究如何用注意力架构改进证据检索。",
    }
    if text in exact:
        return exact[text]

    replacements = [
        ("attention architecture", "注意力架构"),
        ("sparse evidence passages", "分散、稀疏的证据片段"),
        ("related evidence passages", "相关证据片段"),
        ("evidence passage representation", "证据片段的向量表示"),
        ("evidence passage", "证据片段"),
        ("evidence passages", "证据片段"),
        ("attention weight", "注意力权重"),
        ("attention score", "注意力分数"),
        ("retrieval benchmarks", "检索基准"),
        ("retrieval problem", "检索问题"),
        ("retrieval", "检索"),
        ("benchmarks", "基准"),
        ("representation", "向量表示"),
        ("transformed into", "转换成"),
        ("links", "连接"),
        ("connect", "连接"),
        ("evaluated on", "在...上评估"),
        ("methods", "方法"),
        ("method", "方法"),
    ]
    taught = text
    for source, target in replacements:
        pattern = rf"\b{re.escape(source)}\b" if source.isascii() else re.escape(source)
        taught = re.sub(pattern, target, taught, flags=re.IGNORECASE)
    return _compact_user_text(taught, max_chars=max_chars)


def _is_front_matter_candidate(candidate: dict[str, object]) -> bool:
    section = _clean(candidate.get("section")).lower()
    claim_type = _clean(candidate.get("claim_type")).upper()
    return claim_type == "BACKGROUND" and "front" in section or any(
        marker in section for marker in ["front", "title", "author"]
    )


def _expanded_query_terms(value: str) -> set[str]:
    text = _clean(value).lower()
    terms = set(_tokens(text))
    expansions = {
        "稀疏": {"sparse"},
        "证据": {"evidence", "passage", "claim"},
        "片段": {"passage", "evidence"},
        "检索": {"retrieval", "retrieve", "search"},
        "注意力": {"attention"},
        "方法": {"method", "architecture", "model"},
        "机制": {"mechanism", "method", "architecture"},
        "实验": {"experiment", "benchmark", "evaluation"},
        "结果": {"result", "benchmark", "metric"},
        "局限": {"limitation", "weakness", "future"},
        "贡献": {"contribution", "idea"},
        "为什么": {"why", "because", "solve"},
        "处理": {"handle", "solve", "address"},
        "解决": {"solve", "address"},
        "有效": {"effective", "work", "useful"},
        "公式": {"formula", "equation", "symbol"},
        "性状": {"trait", "traits", "phenotype", "phenotypes"},
        "表型": {"trait", "traits", "phenotype", "phenotypes"},
        "根系": {"root", "roots", "rsa"},
        "软件": {"software", "tool"},
        "哪些": {"list", "include", "included", "following", "available"},
        "列举": {"list", "include", "included", "following"},
        "包括": {"include", "included", "following"},
        "问题": {"problem", "challenge", "need", "limitation", "difficulty", "error"},
        "真正": {"problem", "challenge", "need", "limitation"},
        "困难": {"difficulty", "challenge", "problem", "hamper"},
        "痛点": {"problem", "challenge", "limitation", "need"},
    }
    for marker, mapped_terms in expansions.items():
        if marker in text:
            terms.update(mapped_terms)
    reverse = {
        "sparse": {"稀疏"},
        "evidence": {"证据", "片段"},
        "passage": {"证据", "片段"},
        "retrieval": {"检索"},
        "attention": {"注意力"},
        "method": {"方法", "机制"},
        "architecture": {"方法", "机制"},
        "experiment": {"实验"},
        "benchmark": {"实验", "结果"},
        "limitation": {"局限"},
        "formula": {"公式"},
        "trait": {"性状", "表型"},
        "traits": {"性状", "表型"},
        "phenotype": {"性状", "表型"},
        "phenotypes": {"性状", "表型"},
        "root": {"根系"},
        "roots": {"根系"},
        "list": {"哪些", "列举"},
        "include": {"包括", "哪些"},
        "problem": {"问题", "困难", "痛点"},
        "challenge": {"问题", "困难", "挑战"},
        "need": {"问题", "需要", "痛点"},
        "difficulty": {"问题", "困难"},
        "error": {"问题", "误差", "错误"},
    }
    for token in list(terms):
        terms.update(reverse.get(token, set()))
    return terms


def _is_list_question(value: str) -> bool:
    text = _clean(value).lower()
    return any(
        marker in text
        for marker in (
            "哪些",
            "列举",
            "列表",
            "包括什么",
            "包括哪些",
            "what traits",
            "which traits",
            "list the",
            "what are the",
        )
    )


def _focused_evidence_excerpt(value: str, *, query: str, max_chars: int) -> str:
    """Return the query-relevant window instead of always truncating the start."""

    text = _clean(value)
    if len(text) <= max_chars:
        return text
    lowered = text.lower()
    anchor = -1
    if _is_problem_solution_question(query):
        for marker in (
            "we present in this paper",
            "in this study, we introduce",
            "need for",
            "time-consuming",
            "time consuming",
            "errors",
            "root overlap",
            "hampered",
            "challenge",
            "problem",
        ):
            position = lowered.find(marker)
            if position >= 0:
                anchor = position
                break
    if _is_list_question(query):
        for marker in (
            "include the following",
            "list of",
            "traits included",
            "available traits",
            "provided traits",
        ):
            position = lowered.find(marker)
            if position >= 0:
                anchor = position
                break
    if anchor < 0:
        for term in sorted(_expanded_query_terms(query), key=len, reverse=True):
            if len(term) < 4:
                continue
            position = lowered.find(term.lower())
            if position >= 0:
                anchor = position
                break
    if anchor < 0:
        return _compact_user_text(text, max_chars=max_chars)
    start = max(0, anchor - min(140, max_chars // 5))
    end = min(len(text), start + max_chars)
    if start:
        boundary = text.find(" ", start)
        if 0 <= boundary < anchor:
            start = boundary + 1
            end = min(len(text), start + max_chars)
    if end < len(text):
        boundary = text.rfind(" ", start, end)
        if boundary > start:
            end = boundary
    return _compact_user_text(text[start:end], max_chars=max_chars)


def _normalize(value: str) -> str:
    return " ".join(_tokens(value))


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", value) if len(token) > 1]


def _paper_follow_up_suggestions(value: object) -> list[str]:
    suggestions: list[str] = []
    for item in _string_list(value):
        suggestion = _compact_user_text(item, max_chars=120)
        if not suggestion or _is_non_paper_question(suggestion):
            continue
        suggestions.append(suggestion)
        if len(suggestions) >= 3:
            break
    return _unique(suggestions)


def _follow_ups() -> list[str]:
    return [
        "这句话对应论文里的哪条依据？",
        "能用一句话讲清楚这个方法吗？",
        "这个结果之后还剩下什么局限？",
    ]
