from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.core.config import ModelProviderConfig
from researchsensei.llm.client import LLMClient
from researchsensei.web.app import create_app


class ScriptedM4LLM:
    def __init__(self, *, evidence_refs: list[str] | None = None, answer: str = "这是 M4 基于证据生成的中文回答。") -> None:
        self.calls = 0
        self.evidence_refs = evidence_refs or ["paper:b001"]
        self.answer = answer

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        return {
            "answer": self.answer,
            "evidence_refs": self.evidence_refs,
            "uncertainty": "Bound to supplied evidence.",
            "follow_up_suggestions": ["Name the evidence ref."],
        }


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
    assert "先看目标" in full_formula["meaning"]
    assert "参数/符号" in full_formula["meaning"]
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
    assert memory["schema_version"] == "m4_memory"
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
    assert data["expected_answer_points"][0].startswith("你的问题：")
    assert data["answer_format"][0].startswith("你的问题：")
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
    assert data["answer"] == "这是 M4 基于证据生成的中文回答。"
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": True}
    assert data["warnings"] == []
    assert llm.calls == 1


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


def test_m4_ask_rejects_llm_answer_with_unknown_evidence_ref(tmp_path: Path) -> None:
    artifact_dir = _write_m4_artifact_run(tmp_path / "m2_success")
    llm = ScriptedM4LLM(evidence_refs=["paper:made_up"])
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
    assert data["answer"].startswith("重点：")
    assert "核心机制：" in data["answer"]
    assert "对应证据：" in data["answer"]
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["warnings"][0]["code"] == "M4_LLM_FALLBACK"
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
    assert data["answer"].startswith("重点：")
    assert "核心机制：" in data["answer"]
    assert "对应证据：" in data["answer"]
    assert data["evidence_refs"] == ["paper:b001"]
    assert data["used_context"] == {"memory": False, "artifacts": True, "llm": False}
    assert data["warnings"][0]["code"] == "M4_LLM_FALLBACK"
    assert llm.calls == 1


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
    assert "重点：" in data["answer"]


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
    assert "核心机制：" in data["answer"]


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
    assert "对应证据：" in data["answer"]
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
        "phase12_patterns": user_display,
        "phase12_drill": user_display,
        "phase12_drill_degraded": False,
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
