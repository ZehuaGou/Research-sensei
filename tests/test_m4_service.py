from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from researchsensei.m4.service import M4InteractionService


class FakePaperAgent:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self.config = SimpleNamespace(tutor_model="mimo-v2.5")

    def answer(
        self,
        *,
        session_id: str,
        question: str,
        selected_text: str = "",
        model: str = "",
        provider_id: str = "",
    ) -> str:
        self.calls.append(
            {
                "session_id": session_id,
                "question": question,
                "selected_text": selected_text,
                "model": model,
                "provider_id": provider_id,
            }
        )
        if "生成一个能检验真正理解的问题" in question:
            return """{
              "question": "核心方法为什么能解决论文提出的问题？",
              "target_concept": "核心方法",
              "expected_answer_points": ["研究问题", "方法机制", "实验依据"],
              "why_it_matters": "检查理解链条",
              "answer_format": ["结论", "机制", "依据"]
            }"""
        if "评估用户回答" in question:
            return """{
              "score": 0.8,
              "covered_points": ["研究问题", "方法机制"],
              "missing_points": ["实验依据"],
              "misconceptions": [],
              "improvement_steps": ["补充实验结果"],
              "next_question": "哪项实验最关键？",
              "feedback": "方法解释清楚，但证据还不够具体。"
            }"""
        return "论文通过三个连续步骤完成方法，并用对照实验验证。这里的解释来自完整论文会话。"


def _artifacts() -> dict[str, object]:
    return {
        "opencode_analysis": {
            "session_id": "ses-paper",
            "provider_id": "opencode-go",
            "model": "qwen3.7-plus",
            "tutor_model": "mimo-v2.5",
        },
        "parsed_document": {
            "blocks": [
                {
                    "page": 2,
                    "section": "method",
                    "text": "The method links sparse evidence in three stages.",
                    "evidence_ref": "paper:b001",
                },
                {
                    "page": 5,
                    "section": "results",
                    "text": "The controlled experiment improves retrieval accuracy.",
                    "evidence_ref": "paper:b002",
                },
            ]
        },
        "passage_index": {"passages": []},
        "formula_cards": {
            "formula_cards": [
                {
                    "formula_id": "eq001",
                    "original_latex": "y = Wx + b",
                    "plain_summary": "线性变换",
                    "intuition": "先变换再平移",
                    "evidence_ref": "paper:eq001",
                    "formula_origin": "ocr_latex",
                    "formula_ocr_status": "ocr_success",
                }
            ]
        },
    }


def _service(tmp_path: Path) -> tuple[M4InteractionService, FakePaperAgent]:
    agent = FakePaperAgent()
    return (
        M4InteractionService(
            job_id="paper",
            run_dir=tmp_path,
            artifacts=_artifacts(),
            paper_agent=agent,  # type: ignore[arg-type]
        ),
        agent,
    )


def test_default_question_reuses_opencode_session_and_tutor_model(tmp_path: Path) -> None:
    service, agent = _service(tmp_path)

    result = service.answer_question({"question": "请详细解释论文方法。"})

    assert result.status == "SUCCESS"
    assert result.used_context["opencode_session"] is True
    assert result.context_trace.context_mode == "full_paper"
    assert result.context_trace.full_text_complete is True
    assert result.evidence_refs
    assert agent.calls[0]["session_id"] == "ses-paper"
    assert agent.calls[0]["model"] == "mimo-v2.5"
    assert "Markdown 正文" in agent.calls[0]["question"]


def test_evidence_only_is_explicit_and_does_not_call_model(tmp_path: Path) -> None:
    service, agent = _service(tmp_path)

    result = service.answer_question(
        {"question": "实验结果是什么？", "answer_mode": "evidence_only"}
    )

    assert result.status == "SUCCESS"
    assert result.used_context["llm"] is False
    assert result.context_trace.context_mode == "evidence"
    assert "原文位置" in result.answer
    assert agent.calls == []


def test_selection_and_formula_explanation_use_paper_session(tmp_path: Path) -> None:
    service, agent = _service(tmp_path)

    selection = service.explain_selection(
        {"selected_text": "three stages", "user_question": "为什么分三步？"}
    )
    formula = service.explain_formula({"formula_id": "eq001", "symbol": "W"})

    assert selection.status == "SUCCESS"
    assert formula.status == "SUCCESS"
    assert formula.formula_origin == "ocr_latex"
    assert len(agent.calls) == 2
    assert agent.calls[0]["selected_text"] == "three stages"
    assert agent.calls[1]["selected_text"] == "y = Wx + b"


def test_advisor_generation_and_evaluation_use_paper_session(tmp_path: Path) -> None:
    service, agent = _service(tmp_path)

    question = service.advisor_question({"user_question": "方法为什么有效？"})
    evaluation = service.advisor_evaluate(
        {
            "question": question.question,
            "user_answer": "它分三步连接证据，因此解决了稀疏检索问题。",
            "expected_answer_points": question.expected_answer_points,
            "evidence_refs": question.evidence_refs,
        }
    )

    assert question.question == "核心方法为什么能解决论文提出的问题？"
    assert evaluation.score == 0.8
    assert evaluation.missing_points == ["实验依据"]
    assert len(agent.calls) == 2


def test_memory_is_atomic_bounded_and_clearable(tmp_path: Path) -> None:
    service, _agent = _service(tmp_path)

    service.answer_question({"question": "论文方法是什么？"})
    bundle = service.get_memory()

    assert len(bundle.records) == 1
    assert bundle.records[0].source_artifact == "opencode_analysis"
    assert service.memory_path.read_text(encoding="utf-8").startswith("{")
    assert service.clear_memory().records == []


def test_general_chat_is_rejected_without_spending_model_request(tmp_path: Path) -> None:
    service, agent = _service(tmp_path)

    result = service.answer_question({"question": "你好"})

    assert result.status == "DEGRADED"
    assert result.used_context["llm"] is False
    assert agent.calls == []
