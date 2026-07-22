from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.core.config import ModelProviderConfig
from researchsensei.llm.client import LLMClient
from researchsensei.m4.service import _claim_content_supported, _teach_phrase
from researchsensei.web.app import create_app


def test_m4_grounding_accepts_bilingual_root_software_claim() -> None:
    supported, reason = _claim_content_supported(
        "GiA Roots 通过图像分割提取根系表型性状，并提供可扩展的软件工作流。",
        evidence_text=(
            "GiA Roots is extensible software for root system architecture image segmentation, "
            "phenotype trait extraction, and reproducible workflows."
        ),
        claim_type="paper_claim",
    )

    assert supported is True
    assert reason == ""


def test_m4_grounding_rejects_unmentioned_root_software_mechanism() -> None:
    supported, reason = _claim_content_supported(
        "GiA Roots 使用三维重建和命令行接口完成根系分析。",
        evidence_text="GiA Roots is software for two-dimensional root image segmentation.",
        claim_type="paper_claim",
    )

    assert supported is False
    assert reason.startswith("unsupported_specific_concept:")


def test_m4_teaching_translation_does_not_leave_plural_suffixes() -> None:
    translated = _teach_phrase("These methods compare evidence passages.")

    assert "方法s" not in translated
    assert "证据片段s" not in translated


class ScriptedM4LLM:
    def __init__(
        self,
        *,
        evidence_refs: list[str] | None = None,
        answer: str = "这篇论文用注意力结构把分散的证据片段连接起来，让检索可以聚合相关上下文。",
        supporting_quote: str = "The attention architecture links sparse evidence passages to solve the retrieval problem.",
        claims: list[dict[str, object]] | None = None,
        uncertainty: str = "",
    ) -> None:
        self.calls = 0
        self.evidence_refs = evidence_refs or ["paper:b001"]
        self.answer = answer
        self.supporting_quote = supporting_quote
        self.claims = claims
        self.uncertainty = uncertainty
        self.messages = []
        self.configs = []

    async def chat(self, messages, *, config=None):
        raise AssertionError("M4 ask must use structured chat_json")

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        self.messages.append(messages)
        self.configs.append(config)
        claims = self.claims or [
            {
                "text": self.answer,
                "claim_type": "paper_claim",
                "evidence_refs": self.evidence_refs,
                "supporting_quotes": [
                    {"evidence_ref": ref, "quote": self.supporting_quote}
                    for ref in self.evidence_refs
                ],
                "uncertainty": "",
            }
        ]
        return {"claims": claims, "uncertainty": self.uncertainty, "follow_up_suggestions": []}


class FailingM4LLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, *, config=None):
        raise AssertionError("M4 ask must use structured chat_json")

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        raise RuntimeError("simulated llm outage")


class TimeoutM4LLM(FailingM4LLM):
    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        raise RuntimeError("simulated llm request timed out")


def test_m4_anthropic_provider_uses_full_reasoning_output_budget(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM()
    llm.provider = ModelProviderConfig(
        name="cc_switch",
        kind="anthropic_compatible",
        base_url="http://127.0.0.1:15721/v1",
        model="claude-sonnet-4-6",
        auth_header="none",
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "这篇论文的方法是什么？"})

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert llm.calls == 1
    assert llm.configs[0].max_tokens == 12_000
    assert llm.configs[0].disable_thinking is True
    assert llm.configs[0].timeout == 80.0
    assert llm.configs[0].max_retries == 0


def test_m4_interactions_use_registered_m2_artifacts_and_memory(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    selection_response = client.post(
        f"/api/v1/jobs/{job_id}/selection/explain",
        json={"selected_text": "attention architecture", "user_question": "Why is this important?"},
    )
    assert selection_response.status_code == 200
    selection = selection_response.json()
    assert selection["status"] == "SUCCESS"
    assert selection["cited_evidence_refs"] == ["paper:b001"]
    assert selection["cited_passage_ids"] == ["p1"]

    formula_response = client.post(
        f"/api/v1/jobs/{job_id}/formula/explain",
        json={"formula_id": "f1", "symbol": "x"},
    )
    assert formula_response.status_code == 200
    formula = formula_response.json()
    assert formula["formula_id"] == "f1"
    assert formula["symbol"] == "x"
    assert formula["evidence_ref"] == "paper:b001"
    assert formula["formula_origin"] == "mineru_latex"

    full_formula_response = client.post(
        f"/api/v1/jobs/{job_id}/formula/explain",
        json={"formula_id": "f1"},
    )
    assert full_formula_response.status_code == 200
    full_formula = full_formula_response.json()
    assert "公式卡片记录的目标" in full_formula["meaning"]
    assert "公式卡片明确记录的对象" in full_formula["meaning"]
    assert "证据片段的向量表示" in full_formula["meaning"]
    assert "注意力分数" in full_formula["meaning"]
    assert full_formula["symbol"] == ""

    ask_payload = {
        "question": "How does the attention architecture solve the problem?",
        "selected_text": "attention architecture",
    }
    ask_response = client.post(f"/api/v1/jobs/{job_id}/ask", json=ask_payload)
    assert ask_response.status_code == 200
    answer = ask_response.json()
    assert answer["status"] == "SUCCESS"
    assert answer["evidence_refs"] == ["paper:b001"]
    assert answer["memory_refs"] == []

    memory_answer_response = client.post(f"/api/v1/jobs/{job_id}/ask", json=ask_payload)
    assert memory_answer_response.status_code == 200
    memory_answer = memory_answer_response.json()
    assert memory_answer["used_context"] == {"memory": True, "artifacts": False, "llm": False}
    assert memory_answer["memory_refs"]

    advisor_response = client.post(
        f"/api/v1/jobs/{job_id}/advisor/question",
        json={"advisor_mode": "group_meeting"},
    )
    assert advisor_response.status_code == 200
    advisor = advisor_response.json()
    assert "attention architecture" in advisor["question"]
    assert advisor["evidence_refs"] == ["paper:b001"]
    assert advisor["expected_answer_points"]
    assert advisor["answer_format"]
    assert advisor["why_it_matters"]
    assert "evidence_ref" not in " ".join(advisor["expected_answer_points"])

    evaluation_response = client.post(
        f"/api/v1/jobs/{job_id}/advisor/evaluate",
        json={
            "question": advisor["question"],
            "user_answer": "The problem is sparse evidence, and the attention architecture connects passages.",
            "expected_answer_points": advisor["expected_answer_points"],
            "evidence_refs": advisor["evidence_refs"],
        },
    )
    assert evaluation_response.status_code == 200
    evaluation = evaluation_response.json()
    assert evaluation["score"] > 0
    assert evaluation["feedback"]
    assert evaluation["covered_points"]
    assert evaluation["improvement_steps"] or evaluation["score"] >= 0.75
    assert "evidence_ref" not in evaluation["next_question"]
    assert evaluation["evidence_refs"] == ["paper:b001"]

    memory_response = client.get(f"/api/v1/jobs/{job_id}/memory")
    assert memory_response.status_code == 200
    memory = memory_response.json()
    assert memory["schema_version"] == "m4_memory.v2"
    assert memory["job_id"] == job_id
    assert len(memory["records"]) >= 5
    assert {record["memory_type"] for record in memory["records"]} >= {
        "selection_explanation",
        "formula_explanation",
        "interactive_answer",
        "advisor_question",
        "advisor_evaluation",
    }

    job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    artifact_types = {artifact["artifact_type"] for artifact in job_response.json()["artifacts"]}
    assert "m4_memory" in artifact_types

    clear_response = client.delete(f"/api/v1/jobs/{job_id}/memory")
    assert clear_response.status_code == 200
    assert clear_response.json()["status"] == "CLEARED"
    assert clear_response.json()["records"] == []

    cleared_memory_response = client.get(f"/api/v1/jobs/{job_id}/memory")
    assert cleared_memory_response.status_code == 200
    assert cleared_memory_response.json()["records"] == []


def test_m4_rejects_non_user_facing_understanding_status(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "baseline", user_display=False, status="BASELINE_ONLY")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "Can I ask about this paper?"},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["status"] == "BASELINE_ONLY"
    assert detail["message"] == "M4 requires user-facing M2 understanding artifacts."


def test_m4_advisor_respects_downstream_gate(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "advisor_closed", advisor_questions=False)
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    ask_response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "What is the method?"},
    )
    assert ask_response.status_code == 200

    advisor_response = client.post(
        f"/api/v1/jobs/{job_id}/advisor/question",
        json={"advisor_mode": "group_meeting"},
    )
    assert advisor_response.status_code == 403
    detail = advisor_response.json()["detail"]
    assert detail["gate"] == "allowed_downstream.advisor_questions"
    assert detail["message"] == "M4 route requires allowed_downstream.advisor_questions."


def test_m4_advisor_question_can_follow_user_focus(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "advisor_focus")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/advisor/question",
        json={
            "advisor_mode": "group_meeting",
            "user_question": "为什么这个方法能处理稀疏证据？",
            "selected_text": "Attention helps connect scattered evidence.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question_type"] == "custom_focus"
    assert data["user_question"] == "为什么这个方法能处理稀疏证据？"
    assert "为什么这个方法能处理稀疏证据？" in data["question"]
    assert "你选中的这段内容" in data["question"]
    assert data["target_concept"] == "为什么这个方法能处理稀疏证据？"
    assert data["expected_answer_points"][0].startswith("先直接回答")
    assert data["answer_format"][0].startswith("先用一句自然话")
    visible_text = json.dumps(
        {
            "question": data["question"],
            "expected_answer_points": data["expected_answer_points"],
            "answer_format": data["answer_format"],
            "why_it_matters": data["why_it_matters"],
        },
        ensure_ascii=False,
    )
    assert "evidence_ref" not in visible_text
    assert "paper:b001" not in visible_text
    _assert_no_mojibake(data)


def test_m4_advisor_evaluation_gives_specific_missing_points(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "advisor_feedback")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    advisor = client.post(
        f"/api/v1/jobs/{job_id}/advisor/question",
        json={"advisor_mode": "group_meeting"},
    ).json()
    evaluation_response = client.post(
        f"/api/v1/jobs/{job_id}/advisor/evaluate",
        json={
            "question": advisor["question"],
            "user_answer": "It uses attention.",
            "expected_answer_points": advisor["expected_answer_points"],
            "evidence_refs": advisor["evidence_refs"],
        },
    )

    assert evaluation_response.status_code == 200
    evaluation = evaluation_response.json()
    assert 0 < evaluation["score"] < 0.8
    assert evaluation["missing_points"]
    assert evaluation["improvement_steps"]
    assert "问题" in evaluation["feedback"] or "机制" in evaluation["feedback"] or "证据" in evaluation["feedback"]
    assert "evidence_ref" not in evaluation["feedback"]
    assert "evidence_ref" not in evaluation["next_question"]


def test_m4_ask_uses_llm_when_client_is_configured(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "What is the method?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "注意力结构" in data["answer"]
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["claims"] == [
        {
            "text": "这篇论文用注意力结构把分散的证据片段连接起来，让检索可以聚合相关上下文。",
            "evidence_refs": ["paper:b001"],
            "claim_type": "paper_claim",
            "support_status": "SUPPORTED",
            "uncertainty": "",
        }
    ]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": True}
    assert data["warnings"] == []
    assert llm.calls == 1


def test_m4_followup_resolves_previous_turn_without_using_chat_as_evidence(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_followup")
    llm = ScriptedM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    first_question = "论文为什么要用注意力连接稀疏证据？"
    first = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": first_question})
    assert first.status_code == 200

    followup = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "为什么？",
            "conversation_history": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first.json()["answer"]},
            ],
        },
    )

    assert followup.status_code == 200
    data = followup.json()
    assert data["status"] == "SUCCESS"
    assert data["used_context"]["conversation"] is True
    assert data["context_trace"]["continued_from_history"] is True
    assert first_question in data["context_trace"]["focus_question"]
    assert data["context_trace"]["evidence_count"] == 1
    assert data["evidence_refs"] == ["paper:b001"]
    prompt = json.loads(llm.messages[-1][1].content)
    assert prompt["context"]["conversation_focus"]["continued_from_history"] is True
    assert first_question in prompt["context"]["conversation_focus"]["resolved_question"]
    assert "只用于理解指代与追问" in "".join(prompt["output_rules"])
    assert prompt["context"]["allowed_evidence_refs"] == ["paper:b001"]


def test_m4_rejects_legal_ref_when_evidence_does_not_support_claim(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "unsupported_claim")
    llm = ScriptedM4LLM(
        answer="论文在 NASA 数据集上把 F1 提升了 12.5%。",
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "实验结果如何？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["evidence_refs"] == []
    assert data["claims"] == []
    assert "NASA" not in data["answer"]
    assert "12.5" not in data["answer"]
    assert "M4_CLAIM_UNSUPPORTED" in {warning["code"] for warning in data["warnings"]}


def test_m4_keeps_supported_claims_and_drops_unsupported_claims(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "partial_claims")
    quote = "The attention architecture links sparse evidence passages to solve the retrieval problem."
    llm = ScriptedM4LLM(
        claims=[
            {
                "text": "论文用注意力结构连接分散的证据片段，以回应检索问题。",
                "claim_type": "paper_claim",
                "evidence_refs": ["paper:b001"],
                "supporting_quotes": [{"evidence_ref": "paper:b001", "quote": quote}],
                "uncertainty": "",
            },
            {
                "text": "论文还在 NASA 数据集上把 F1 提升了 12.5%。",
                "claim_type": "paper_claim",
                "evidence_refs": ["paper:b001"],
                "supporting_quotes": [{"evidence_ref": "paper:b001", "quote": quote}],
                "uncertainty": "",
            },
        ]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "这篇论文的方法是什么？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["evidence_refs"] == ["paper:b001"]
    assert len(data["claims"]) == 1
    assert data["claims"][0]["support_status"] == "SUPPORTED"
    assert "注意力结构" in data["answer"]
    assert "NASA" not in data["answer"]
    assert "M4_CLAIM_UNSUPPORTED" in {warning["code"] for warning in data["warnings"]}


def test_m4_uses_audited_paper_card_as_cross_language_validation_bridge(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "cross_language_claim")
    paper_card_path = artifact_dir / "paper_card.json"
    paper_card = json.loads(paper_card_path.read_text(encoding="utf-8"))
    paper_card["problem"] = {
        "text": "稀疏的证据片段让检索过程不稳定。",
        "evidence_ref": "paper:b001",
    }
    _write_json(paper_card_path, paper_card)
    quote = "The attention architecture links sparse evidence passages to solve the retrieval problem."
    llm = ScriptedM4LLM(
        claims=[{
            "text": (
                "论文真正处理的是证据片段分散、导致 retrieval 检索过程脆弱的问题；"
                "当相关信息没有自然聚集在同一处时，检索难以稳定找到足够依据，"
                "因此论文把需要解决的核心障碍界定为如何连接这些稀疏证据片段。"
                "这一问题定义强调的是证据组织和检索可靠性，而不是凭空增加新的外部信息。"
            ),
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{"evidence_ref": "paper:b001", "quote": quote}],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "论文解决了什么问题？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["evidence_refs"] == ["paper:b001"]
    assert "证据片段分散" in data["answer"]


def test_m4_accepts_concise_problem_answer_after_claim_grounding(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "concise_problem")
    quote = "The attention architecture links sparse evidence passages to solve the retrieval problem."
    llm = ScriptedM4LLM(
        claims=[{
            "text": "论文解决稀疏证据片段让检索不稳定的问题，并用注意力结构连接相关片段，使检索能够聚合分散依据。",
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{"evidence_ref": "paper:b001", "quote": quote}],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "论文解决了什么问题？"})

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_m4_placeholder_card_is_not_presented_as_grounded_evidence(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "placeholder_card")
    _write_json(
        artifact_dir / "paper_card.json",
        {
            "paper_id": "paper",
            "title": "Placeholder Card",
            "one_sentence_summary": "UNKNOWN",
            "evidence_refs": ["paper:b001"],
            "problem": {"text": "证据不足，暂不展开。", "evidence_ref": "paper:b001"},
            "core_idea": {"text": "核心想法围绕 Image-Analysis 形成方法改进。", "evidence_ref": "paper:b001"},
            "method_overview": {"text": "证据不足，暂不展开。", "evidence_ref": "paper:b001"},
        },
    )
    client = TestClient(
        create_app(workspace_root=tmp_path / "workspace", allowed_local_roots=[tmp_path])
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这篇论文真正解决了什么问题？", "answer_mode": "evidence_only"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["evidence_refs"] == []
    assert "证据不足，暂不展开" not in data["answer"]
    assert "M4_CONTEXT_MISSING" in {warning["code"] for warning in data["warnings"]}


def test_m4_problem_question_rejects_method_only_answer(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "method_only_problem_answer")
    llm = ScriptedM4LLM(
        answer="论文采用注意力结构连接分散的证据片段，并聚合相关上下文来完成检索流程。",
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这篇论文真正解决了什么问题？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert "M4_LLM_LOW_QUALITY" in {warning["code"] for warning in data["warnings"]}
    assert data["evidence_refs"] == []
    assert "采用注意力结构连接分散的证据片段" not in data["answer"]


def test_m4_excludes_blocked_raw_formula_from_grounded_prompt(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "blocked_raw_formula")
    passage_index = json.loads((artifact_dir / "passage_index.json").read_text(encoding="utf-8"))
    passage_index["passages"].append({
        "passage_id": "p2",
        "text": "lines = parent root",
        "section": "full_text",
        "evidence_refs": ["paper:b002"],
        "formula_origins": ["raw_formula_text"],
        "risk_flags": ["RAW_FORMULA_TEXT"],
    })
    _write_json(artifact_dir / "passage_index.json", passage_index)
    _write_json(
        artifact_dir / "formula_cards.json",
        {
            "paper_id": "paper",
            "formula_cards": [{
                "formula_id": "bad-formula",
                "plain_summary": "lines = parent root",
                "formula_origin": "raw_formula_text",
                "coverage_status": "BLOCKED_RAW_ONLY",
                "warnings": ["RAW_FORMULA_TEXT"],
                "evidence_ref": "paper:b002",
            }],
        },
    )
    llm = ScriptedM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这篇论文的方法和公式是什么？"},
    )

    assert response.status_code == 200
    prompt = json.loads(llm.messages[0][-1].content)
    assert "paper:b002" not in prompt["context"]["allowed_evidence_refs"]
    assert "lines = parent root" not in json.dumps(prompt, ensure_ascii=False)


def test_m4_accepts_server_source_quote_id_without_model_recopying_text(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "source_quote_id")
    llm = ScriptedM4LLM(
        claims=[{
            "text": "论文解决稀疏证据片段让检索不稳定的问题，并用注意力结构连接相关片段，使检索能够聚合分散依据。",
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{
                "evidence_ref": "paper:b001",
                "quote_id": "source_quote_001",
                "quote": "模型不再需要逐字复制这段英文原文。",
            }],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "论文解决了什么问题？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["evidence_refs"] == ["paper:b001"]
    assert "检索不稳定" in data["answer"]
    prompt = json.loads(llm.messages[-1][1].content)
    source_rows = [
        row
        for row in prompt["context"]["retrieved_evidence"]
        if row.get("quote_id") == "source_quote_001"
    ]
    assert source_rows == [{
        "source": "passage_index",
        "evidence_ref": "paper:b001",
        "text": "The attention architecture links sparse evidence passages to solve the retrieval problem.",
        "quote_id": "source_quote_001",
    }]


def test_m4_resolves_model_quote_paraphrase_to_server_source(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "source_quote_resolution")
    llm = ScriptedM4LLM(
        claims=[{
            "text": "论文解决稀疏证据片段让检索不稳定的问题，并用注意力结构连接相关片段，使检索能够聚合分散依据。",
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{
                "evidence_ref": "paper:b001",
                "quote": "The model uses attention to connect scattered evidence.",
            }],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "论文解决了什么问题？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["evidence_refs"] == ["paper:b001"]
    assert "检索不稳定" in data["answer"]


def test_m4_does_not_trust_unknown_quote_id_for_unsupported_claim(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "unknown_source_quote_id")
    llm = ScriptedM4LLM(
        claims=[{
            "text": "论文在 NASA 数据集上把 F1 提升了 12.5%。",
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{
                "evidence_ref": "paper:b001",
                "quote_id": "source_quote_999",
                "quote": "这不是论文原文。",
            }],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "论文解决了什么问题？"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["claims"] == []
    assert data["warnings"][0]["detail"] == "supporting_quote_not_verbatim"
    assert "NASA" not in data["answer"]


def test_m4_ask_expands_llm_context_for_chinese_focus_question(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(
        answer=(
            "重点：稀疏证据会让检索变脆弱，论文用注意力结构把分散证据片段连接起来。"
            "\n\n问题：障碍是证据分散。核心机制：attention architecture 建立片段之间的联系。"
            "\n\n为什么有效：它把检索问题转成可聚合的证据连接。对应证据：正文方法段说明该结构连接 sparse evidence passages。"
        )
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "为什么这个方法能处理稀疏证据？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": True}
    assert data["evidence_refs"] == ["paper:b001"]
    assert "稀疏证据" in data["answer"]
    prompt_text = llm.messages[0][1].content
    assert "allowed_evidence_refs" in prompt_text
    assert "paper:b001" in prompt_text
    assert "sparse evidence passages" in prompt_text
    assert "attention architecture" in prompt_text
    assert "front_matter" not in prompt_text


def test_m4_list_question_retrieves_late_detail_window_for_shared_evidence_ref(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m4_trait_list")
    passage_path = artifact_dir / "passage_index.json"
    passage_index = json.loads(passage_path.read_text(encoding="utf-8"))
    passage_index["passages"].append({
        "passage_id": "p2",
        "text": (
            ("Earlier implementation details do not enumerate measurements. " * 25)
            + "Trait selection lets users choose from a list of established RSA traits. "
            + "The traits include the following: aspect ratio, average root width, "
            + "network depth, network volume, and specific root length."
        ),
        "section": "method",
        "evidence_refs": ["paper:b001"],
    })
    _write_json(passage_path, passage_index)
    llm = ScriptedM4LLM(
        claims=[{
            "text": "软件提供的根系结构性状包括：长宽比、平均根宽、网络深度、网络体积和比根长。",
            "claim_type": "paper_claim",
            "evidence_refs": ["paper:b001"],
            "supporting_quotes": [{
                "evidence_ref": "paper:b001",
                "quote_id": "source_quote_001",
                "quote": "",
            }],
            "uncertainty": "",
        }]
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这个软件具体提供了哪些根系结构性状？"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert "网络体积" in response.json()["answer"]
    prompt = json.loads(llm.messages[-1][1].content)
    source_rows = [
        row
        for row in prompt["context"]["retrieved_evidence"]
        if row.get("source") == "passage_index"
    ]
    list_rows = [row for row in source_rows if "aspect ratio" in row["text"]]
    assert len(list_rows) == 1
    assert "network depth" in list_rows[0]["text"]
    assert "network volume" in list_rows[0]["text"]
    assert "specific root length" in list_rows[0]["text"]
    assert list_rows[0]["quote_id"].startswith("source_quote_")
    assert len(list_rows[0]["text"]) <= 900

    llm.claims = [{
        "text": "软件提供的根系结构性状包括：长宽比、平均根宽、网络深度、网络体积和叶绿素浓度。",
        "claim_type": "paper_claim",
        "evidence_refs": ["paper:b001"],
        "supporting_quotes": [{
            "evidence_ref": "paper:b001",
            "quote_id": "source_quote_001",
            "quote": "",
        }],
        "uncertainty": "",
    }]
    unsupported = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这个软件具体提供了哪些根系结构性状？"},
    )
    assert unsupported.status_code == 200
    assert unsupported.json()["status"] == "DEGRADED"
    assert unsupported.json()["warnings"][0]["detail"] == "unsupported_trait_item"


def test_m4_ask_fallback_answers_chinese_focus_with_relevant_evidence(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "为什么这个方法能处理稀疏证据？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["answer"].startswith("我先按“为什么这个方法能处理稀疏证据？”来理解")
    assert "贴着你的问题看，可以追到这些依据" in data["answer"]
    assert "用注意力架构连接分散的证据片段" in data["answer"]
    assert "证据片段太分散" in data["answer"]
    assert "它不是只重复论文目标" in data["answer"]
    assert "重点：" not in data["answer"]
    assert "核心机制：" not in data["answer"]
    assert "attention architecture links sparse evidence passages" not in data["answer"]
    assert "paper:b001" not in data["answer"]


def test_m4_ask_clarifies_underspecified_question(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这个怎么理解？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["evidence_refs"] == []
    assert data["used_context"] == {"memory": False, "artifacts": False, "llm": False}
    assert data["warnings"][0]["code"] == "QUESTION_UNDERSPECIFIED"
    assert "我先追问一下" in data["answer"]
    assert "你说的“这个怎么理解？”是想问哪一块" in data["answer"]
    assert "方法" in data["answer"]
    assert data["follow_up_suggestions"]


def test_m4_ask_limitation_question_does_not_invent_missing_limitations(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这个方法还有什么局限？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["warnings"][0]["code"] == "LIMITATION_EVIDENCE_MISSING"
    assert "没有给出可追踪的局限证据" in data["answer"]
    assert "不能硬编局限" in data["answer"]
    assert "没有足够依据判断具体局限" in data["answer"]


def test_m4_selected_text_followup_explains_why_it_matters(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "这句话为什么重要？",
            "selected_text": "The attention architecture links sparse evidence passages to solve the retrieval problem.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_refs"] == ["paper:b001"]
    assert "这段内容最接近论文中“方法”部分的证据" in data["answer"]
    assert "它重要在于" in data["answer"]
    assert "把论文想解决的困难和论文采用的机制接到了一起" in data["answer"]
    assert "读理论时先抓这条连接" in data["answer"]
    assert "The attention architecture links sparse evidence passages" not in data["answer"]
    assert "可以这样理解：这句话为什么重要" not in data["answer"]


def test_m4_ask_answers_runtime_model_question_without_paper_fallback(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    provider = ModelProviderConfig(
        name="cc_switch",
        kind="anthropic_compatible",
        base_url="http://127.0.0.1:15721/v1",
        api_key_env="",
        model="claude-sonnet-4-6",
        auth_header="none",
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=LLMClient(provider),
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "你现在用的是哪个模型"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "claude-sonnet-4-6" in data["answer"]
    assert "ccswitch" in data["answer"]
    assert "DDMT" not in data["answer"]
    assert data["evidence_refs"] == []
    assert data["used_context"] == {"memory": False, "artifacts": False, "llm": False}


def test_m4_ask_answers_identity_question_without_paper_fallback(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    provider = ModelProviderConfig(
        name="cc_switch",
        kind="anthropic_compatible",
        base_url="http://127.0.0.1:15721/v1",
        api_key_env="",
        model="claude-sonnet-4-6",
        auth_header="none",
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=LLMClient(provider),
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "你现在是谁"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "M4 论文助教" in data["answer"]
    assert "claude-sonnet-4-6" in data["answer"]
    assert "DDMT" not in data["answer"]
    assert data["evidence_refs"] == []
    assert data["used_context"] == {"memory": False, "artifacts": False, "llm": False}


def test_m4_ask_handles_general_chat_without_paper_fallback(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(answer="不应该调用大模型")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "你好"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert "M4 论文助教" in data["answer"]
    assert "attention architecture" not in data["answer"]
    assert data["evidence_refs"] == []
    assert data["used_context"] == {"memory": False, "artifacts": False, "llm": False}
    assert llm.calls == 0


def test_m4_ask_rejects_off_topic_tasks_without_memory_pollution(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    for question in ["今天天气怎么样？", "帮我写一段 Python 代码", "给我讲个笑话", "Can you write a poem?"]:
        response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": question})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DEGRADED"
        assert "M4 论文助教" in data["answer"]
        assert "attention architecture" not in data["answer"]
        assert data["evidence_refs"] == []
        assert data["used_context"] == {"memory": False, "artifacts": False, "llm": False}
        assert data["warnings"][0]["code"] == "M4_GENERAL_CHAT"

    assert llm.calls == 0
    memory_response = client.get(f"/api/v1/jobs/{job_id}/memory")
    assert memory_response.status_code == 200
    assert memory_response.json()["records"] == []

    paper_response = client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "What is the method?"})
    assert paper_response.status_code == 200
    paper_answer = paper_response.json()
    assert paper_answer["status"] == "SUCCESS"
    assert paper_answer["used_context"] == {"memory": False, "artifacts": True, "llm": True}
    assert paper_answer["memory_refs"] == []
    assert llm.calls == 1


def test_m4_user_facing_fallbacks_do_not_contain_mojibake(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)
    responses = [
        client.post(f"/api/v1/jobs/{job_id}/selection/explain", json={"selected_text": ""}),
        client.post(f"/api/v1/jobs/{job_id}/formula/explain", json={"formula_id": "missing"}),
        client.post(f"/api/v1/jobs/{job_id}/ask", json={}),
        client.post(f"/api/v1/jobs/{job_id}/ask", json={"question": "\u4f60\u597d"}),
    ]

    for response in responses:
        assert response.status_code == 200
        _assert_no_mojibake(response.json())


def test_m4_ask_keeps_verified_artifact_answer_when_llm_request_fails(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = FailingM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "What is the method?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert "没有拿到可用的大模型解释" not in data["answer"]
    assert data["evidence_refs"]
    assert data["claims"][0]["support_status"] == "ARTIFACT_DERIVED"
    assert "没有使用未经验证的模型输出" in data["uncertainty"]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["warnings"][-1]["code"] == "M4_LLM_REQUEST_FAILED"
    assert llm.calls == 1


def test_m4_evidence_only_returns_before_llm_and_does_not_persist_preview(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "evidence_first")
    llm = TimeoutM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "说得再详细一些，这到底是什么、怎么实现的？",
            "selected_text": "用中文讲透这篇论文：本文提出一种连接稀疏证据的方法。",
            "context_scope": "selection",
            "answer_mode": "evidence_only",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    assert data["evidence_refs"]
    assert data["claims"][0]["support_status"] == "ARTIFACT_DERIVED"
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["context_trace"]["selected_text_used"] is True
    assert llm.calls == 0
    assert client.get(f"/api/v1/jobs/{job_id}/memory").json()["records"] == []


def test_m4_paper_card_context_timeout_keeps_verified_answer(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "paper_card_timeout")
    llm = TimeoutM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "说得再详细一些，这到底是什么、怎么实现的？",
            "selected_text": "用中文讲透这篇论文：本文提出一种连接稀疏证据的方法。",
            "context_scope": "selection",
            "answer_mode": "enhanced",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["answer"]
    assert data["evidence_refs"]
    assert data["warnings"][-1]["code"] == "M4_LLM_TIMEOUT"
    assert "没有拿到可用的大模型解释" not in data["answer"]
    assert "没有使用未经验证的模型输出" in data["uncertainty"]
    assert llm.calls == 1


def test_m4_selection_timeout_keeps_verified_artifact_explanation(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "selection_timeout")
    llm = TimeoutM4LLM()
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "请解释这段话。",
            "selected_text": "The attention architecture links sparse evidence passages.",
            "context_scope": "selection",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["claims"][0]["support_status"] == "ARTIFACT_DERIVED"
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["context_trace"]["scope"] == "selection"
    assert data["context_trace"]["evidence_count"] == 1
    assert data["warnings"][-1]["code"] == "M4_LLM_TIMEOUT"
    assert "没有拿到可用的大模型解释" not in data["answer"]
    assert "没有使用未经验证的模型输出" in data["uncertainty"]
    assert llm.calls == 1


def test_m4_ask_rejects_english_heavy_llm_answer(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(
        answer=(
            "The selected text is best treated as part of the paper's method section. "
            "It supports the local claim and repeats the equation source without translating it."
        )
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "What is the method?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert "没有拿到可用的大模型解释" in data["answer"]
    assert data["evidence_refs"] == []
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert "M4_CLAIM_UNSUPPORTED" in {warning["code"] for warning in data["warnings"]}
    assert llm.calls == 1


def test_m4_example_question_rejects_abstract_llm_answer(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(answer="这篇论文通过一个方法解决问题，并且整体效果更好。")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "举个例子详细说明"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert "没有拿到可用的大模型解释" in data["answer"]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert "M4_CLAIM_UNSUPPORTED" in {warning["code"] for warning in data["warnings"]}
    assert llm.calls == 1


def test_m4_example_fallback_does_not_invent_spectral_residual_from_broad_keywords(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "generic_anomaly")
    _write_json(
        artifact_dir / "paper_card.json",
        {
            "paper_id": "paper",
            "title": "Generic Time-series Detector",
            "one_sentence_summary": "A paper about time series anomaly detection.",
            "evidence_refs": ["paper:b001"],
            "problem": {"text": "The task is time series anomaly detection.", "evidence_ref": "paper:b001"},
            "core_idea": {"text": "Learn a detector from time-series observations.", "evidence_ref": "paper:b001"},
            "method_overview": {"text": "The detector assigns an anomaly score.", "evidence_ref": "paper:b001"},
            "experiment_summary": {"text": "UNKNOWN", "evidence_ref": "paper:b001"},
        },
    )
    _write_json(
        artifact_dir / "claim_evidence.json",
        {
            "paper_id": "paper",
            "claims": [
                {
                    "claim_id": "c1",
                    "evidence_ref": "paper:b001",
                    "passage_id": "p1",
                    "claim_type": "METHOD",
                    "claim_text": "The detector assigns an anomaly score to time-series observations.",
                    "quote_or_summary": "The detector assigns an anomaly score to time-series observations.",
                    "source_sentence": "The detector assigns an anomaly score to time-series observations.",
                    "section": "method",
                }
            ],
        },
    )
    _write_json(
        artifact_dir / "passage_index.json",
        {
            "paper_id": "paper",
            "passages": [
                {
                    "passage_id": "p1",
                    "text": "The detector assigns an anomaly score to time-series observations.",
                    "section": "method",
                    "evidence_refs": ["paper:b001"],
                }
            ],
        },
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "请给这个 time series anomaly detection 方法举例。"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["warnings"][0]["code"] == "M4_EXAMPLE_EVIDENCE_INSUFFICIENT"
    assert "傅里叶" not in data["answer"]
    assert "谱残差" not in data["answer"]
    assert "阈值 τ" not in data["answer"]
    assert "公式卡片和证据" in data["answer"]


def test_m4_example_question_includes_formula_context_and_rejects_external_threshold_rule(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    _write_json(artifact_dir / "formula_cards.json", {
        "paper_id": "paper",
        "formula_cards": [
            {
                "formula_id": "sr_threshold",
                "purpose": "用显著性相对局部平均值的偏离判断时间点是否异常。",
                "plain_summary": "如果显著性相对局部平均值超过阈值 tau，就输出异常标签。",
                "symbols": [
                    {"symbol": "S(x_i)", "meaning": "第 i 个时间点的显著性分数。"},
                    {"symbol": "\\overline{S(x_i)}", "meaning": "第 i 个时间点附近的局部平均显著性。"},
                    {"symbol": "\\tau", "meaning": "异常判定阈值。"},
                ],
                "terms": [],
                "intuition": "它判断的是某个点是否比附近背景显著得多。",
                "numeric_example": "INSUFFICIENT_EVIDENCE",
                "what_if_removed": "方法会缺少从显著性分数到异常标签的判定步骤。",
                "weight_sensitivity": "阈值越大，越少时间点会被判成异常。",
                "formula_origin": "source_latex",
                "formula_ocr_status": "not_required",
                "formula_explanation_status": "source_exact",
                "evidence_ref": "paper:eq003",
            }
        ],
    })
    llm = ScriptedM4LLM(
        answer=(
            "举个例子：输入 [10, 11, 10, 60, 11]。第一步先得到每个点的显著性分数，"
            "第二步如果 S_i > μ_S + 3σ_S 就输出 1，否则输出 0。"
        )
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "举个具体例子详细说明。"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert "M4_CLAIM_UNSUPPORTED" in {warning["code"] for warning in data["warnings"]}
    prompt_text = llm.messages[0][1].content
    assert "paper:eq003" in prompt_text
    assert "\\overline{S(x_i)}" in prompt_text
    assert "公式、阈值、数值、数据集、指标和实验结果" in prompt_text


def test_m4_ask_strips_internal_refs_from_user_facing_answer(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(
        answer=(
            "重点：方法核心是用注意力连接分散证据（证据b001）。\n"
            "问题：旧方法难以建模分散依赖。\n"
            "核心机制：用注意力结构聚合相关片段。\n"
            "对应证据：paper:b001\n"
            "记忆：m4_old_answer"
        )
    )
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
            llm_client=llm,
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "请讲清楚这篇论文的核心方法。"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_refs"] == ["paper:b001"]
    assert "paper:b001" not in data["answer"]
    assert "b001" not in data["answer"]
    assert "m4_old_answer" not in data["answer"]
    assert "我先抓最核心的点：" in data["answer"]
    assert "重点：" not in data["answer"]


def test_m4_paper_level_question_ignores_front_matter_selection(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={
            "question": "请用中文讲清楚这篇论文的核心方法。",
            "selected_text": "用中文讲透这篇论文：A paper about attention architecture for evidence retrieval.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_refs"] == ["paper:b001"]
    assert "标题和作者" not in data["answer"]
    assert "做法上" in data["answer"]
    assert "核心机制：" not in data["answer"]


def test_m4_evidence_question_uses_structured_claim_refs_not_front_matter(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )
    job_id = _register_artifact_job(client, artifact_dir)

    response = client.post(
        f"/api/v1/jobs/{job_id}/ask",
        json={"question": "这条结论对应哪条证据？"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_refs"] == ["paper:b001"]
    assert "paper:b000" not in data["evidence_refs"]
    assert "更完整的证据边界" in data["answer"]
    assert "对应证据：" not in data["answer"]
    assert "paper:b001" not in data["answer"]


def _register_artifact_job(client: TestClient, artifact_dir: Path) -> str:
    response = client.post("/api/v1/documents/parse", data={"local_path": str(artifact_dir)})
    assert response.status_code == 200
    return response.json()["job_id"]


def _write_m4_artifact_run(
    root: Path,
    *,
    user_display: bool = True,
    status: str = "SUCCESS",
    advisor_questions: bool | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    advisor_gate = user_display if advisor_questions is None else advisor_questions
    downstream = {
        "reading_display": user_display,
        "learning_patterns": user_display,
        "learning_drills": user_display,
        "learning_drills_degraded": False,
        "advisor_questions": advisor_gate,
    }
    component_status = {
        "paper_card": "SUCCESS" if user_display else "BASELINE",
        "formula_cards": "SUCCESS" if user_display else "BASELINE",
        "teaching_cards": "SUCCESS" if user_display else "BASELINE",
        "llm": "SUCCESS" if user_display else "SKIPPED",
        "evidence_pack": "SUCCESS" if user_display else "SKIPPED",
        "audit": "SUCCESS" if user_display else "SKIPPED",
    }
    _write_json(root / "source_status.json", {
        "source_type": "m1_canonical_bundle",
        "original_input": "m1",
        "resolved_path": str(root / "canonical_paper.md"),
        "status": "resolved",
        "content_type": "text/markdown",
        "size_bytes": 100,
    })
    _write_json(root / "canonical_status.json", {
        "paper_id": "paper",
        "title": "M4 Artifact Paper",
        "canonicalization_status": "success",
        "m2_ready": True,
    })
    _write_json(root / "understanding_status.json", {
        "schema_version": "understanding_status",
        "paper_id": "paper",
        "status": status,
        "blocking_reason": "" if user_display else "NO_LLM_CLIENT",
        "warnings": [],
        "allowed_for_user_display": user_display,
        "allowed_downstream": downstream,
        "component_status": component_status,
        "checked_artifacts": ["paper_card", "formula_cards", "teaching_cards"],
    })
    _write_json(root / "passage_index.json", {
        "paper_id": "paper",
        "passages": [
            {
                "passage_id": "p0",
                "text": "M4 Artifact Paper. Alice Author, Bob Author.",
                "section": "front_matter",
                "evidence_refs": ["paper:b000"],
            },
            {
                "passage_id": "p1",
                "text": "The attention architecture links sparse evidence passages to solve the retrieval problem.",
                "section": "method",
                "evidence_refs": ["paper:b001"],
                "formula_origins": ["mineru_latex"],
                "formula_ocr_statuses": ["not_required"],
            },
        ],
    })
    _write_json(root / "claim_evidence.json", {
        "paper_id": "paper",
        "claims": [
            {
                "claim_id": "c0",
                "evidence_ref": "paper:b000",
                "passage_id": "p0",
                "claim_type": "BACKGROUND",
                "claim_text": "The paper title and authors are listed in the front matter.",
                "quote_or_summary": "M4 Artifact Paper. Alice Author, Bob Author.",
                "source_sentence": "M4 Artifact Paper. Alice Author, Bob Author.",
                "section": "front_matter",
            },
            {
                "claim_id": "c1",
                "evidence_ref": "paper:b001",
                "passage_id": "p1",
                "claim_type": "METHOD",
                "claim_text": "The attention architecture links sparse evidence passages.",
                "quote_or_summary": "The attention architecture links sparse evidence passages to solve the retrieval problem.",
                "source_sentence": "The attention architecture links sparse evidence passages to solve the retrieval problem.",
                "section": "method",
                "formula_origin": "mineru_latex",
                "formula_ocr_status": "not_required",
            },
        ],
    })
    _write_json(root / "quality_report.json", {"paper_id": "paper", "findings": []})
    _write_json(root / "paper_card.json", {
        "paper_id": "paper",
        "title": "M4 Artifact Paper",
        "one_sentence_summary": "A paper about attention architecture for evidence retrieval.",
        "evidence_refs": ["paper:b000", "paper:b001"],
        "problem": {"text": "Sparse evidence passages make retrieval brittle.", "evidence_ref": "paper:b001"},
        "core_idea": {"text": "Use attention to connect related evidence passages.", "evidence_ref": "paper:b001"},
        "method_overview": {"text": "An attention architecture links sparse evidence passages.", "evidence_ref": "paper:b001"},
        "experiment_summary": {"text": "The method is evaluated on retrieval benchmarks.", "evidence_ref": "paper:b001"},
    })
    _write_json(root / "formula_cards.json", {
        "paper_id": "paper",
        "formula_cards": [{
            "formula_id": "f1",
            "purpose": "Scores each evidence passage with an attention weight.",
            "plain_summary": "x is transformed into an attention score.",
            "symbols": [{"symbol": "x", "meaning": "the evidence passage representation"}],
            "formula_origin": "mineru_latex",
            "formula_ocr_status": "not_required",
            "formula_explanation_status": "parser_derived",
            "evidence_ref": "paper:b001",
        }],
    })
    _write_json(root / "teaching_cards.json", {
        "paper_id": "paper",
        "teaching_cards": [{
            "card_id": "t1",
            "title": "Attention as retrieval glue",
            "human_explanation": "Attention helps connect scattered evidence.",
            "evidence_refs": ["paper:b001"],
            "advisor_questions": ["Why is attention useful here?"],
        }],
    })
    _write_json(root / "m2_run_summary.json", {"paper_id": "paper", "status": status})
    return root


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _assert_no_mojibake(data: object) -> None:
    text = json.dumps(data, ensure_ascii=False)
    markers = _m4_mojibake_markers()
    assert [marker for marker in markers if marker in text] == []


def _m4_mojibake_markers() -> list[str]:
    normal_snippets = [
        "\u6ca1\u6709\u6536\u5230",
        "\u89e3\u91ca\u8bc1\u636e",
        "\u8bba\u6587\u52a9\u6559",
        "\u516c\u5f0f\u5361\u7247",
        "\u7814\u7a76\u95ee\u9898",
        "\u65b9\u6cd5\u673a\u5236",
        "\u5bf9\u5e94\u8bc1\u636e",
    ]
    markers: set[str] = set()
    for snippet in normal_snippets:
        encoded = snippet.encode("utf-8")
        for codec in ("gbk", "cp936"):
            try:
                markers.add(encoded.decode(codec))
            except UnicodeDecodeError:
                markers.add(encoded.decode(codec, errors="ignore"))
                markers.add(encoded.decode(codec, errors="replace"))
    markers.discard("")
    return sorted(markers, key=len, reverse=True)
