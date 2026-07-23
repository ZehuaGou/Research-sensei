from __future__ import annotations

import json
from pathlib import Path

import fitz
import httpx

from researchsensei.core.config import OpenCodeConfig
from researchsensei.ingestion.opencode_agent import OpenCodePaperAgent, OpenCodeServerClient
from researchsensei.tutor.service import PaperTutorService


def _pdf(path: Path) -> None:
    document = fitz.open()
    first = document.new_page()
    first.insert_text((72, 72), "A Visual Paper\nAbstract\nWe introduce a reliable method.")
    second = document.new_page()
    second.insert_text((72, 72), "Methods\nThe objective is shown below.")
    document.save(path)
    document.close()


def test_opencode_agent_preserves_page_text_and_adds_visual_semantics(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    _pdf(pdf_path)
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/global/health":
            return httpx.Response(200, json={"healthy": True, "version": "test"})
        if request.url.path == "/provider":
            return httpx.Response(
                200,
                json={
                    "all": [
                        {
                            "id": "opencode-go",
                            "models": {
                                "deepseek-v4-flash": {
                                    "capabilities": {
                                        "attachment": False,
                                        "input": {"text": True, "image": False, "pdf": False},
                                    }
                                },
                                "qwen3.7-plus": {
                                    "capabilities": {
                                        "attachment": True,
                                        "input": {"text": True, "image": True, "pdf": False},
                                    }
                                },
                            },
                        }
                    ],
                    "connected": ["opencode-go"],
                    "default": {},
                },
            )
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_test_paper"})
        if request.url.path == "/session/ses_test_paper/message":
            payload = {
                "pages": [
                    {
                        "page": 1,
                        "paper_title": "A Visual Paper",
                        "printed_page": "1",
                        "section": "abstract",
                        "headings": ["A Visual Paper", "Abstract"],
                        "formulas": [],
                        "figures": [],
                        "tables": [],
                    },
                    {
                        "page": 2,
                        "paper_title": "",
                        "printed_page": "2",
                        "section": "method",
                        "headings": ["Methods"],
                        "formulas": [
                            {
                                "latex": "L = x^2",
                                "equation_number": "(1)",
                                "context_before": "The objective is",
                                "context_after": "minimized during training",
                            }
                        ],
                        "figures": [
                            {
                                "label": "Figure 1",
                                "caption": "Method overview",
                                "description": "Two-stage pipeline",
                            }
                        ],
                        "tables": [],
                    },
                ]
            }
            return httpx.Response(
                200,
                json={
                    "info": {"id": "msg_test"},
                    "parts": [{"type": "text", "text": json.dumps(payload)}],
                },
            )
        return httpx.Response(404, json={"error": "unexpected path"})

    config = OpenCodeConfig(
        enabled=True,
        base_url="http://opencode.test",
        auto_start=False,
        model="deepseek-v4-flash",
        page_batch_size=2,
        max_pages=2,
        render_scale=1.0,
    )
    server = OpenCodeServerClient(
        config,
        directory=tmp_path,
        transport=httpx.MockTransport(handler),
    )
    agent = OpenCodePaperAgent(config, directory=tmp_path, client=server)

    document = agent.ingest_path(pdf_path, paper_id="paper-1")

    assert document.parser_name == "opencode_pdf_agent+pymupdf"
    assert {block.page for block in document.blocks if block.page} == {1, 2}
    formula = next(block for block in document.blocks if block.type.value == "formula")
    assert formula.formula_latex == "L = x^2"
    assert formula.formula_origin == "ocr_latex"
    assert formula.formula_page == 2
    assert any(block.type.value == "figure" for block in document.blocks)
    analysis = json.loads((tmp_path / "opencode_analysis.json").read_text(encoding="utf-8"))
    assert analysis["model"] == "qwen3.7-plus"
    assert analysis["session_id"] == "ses_test_paper"
    assert (tmp_path / "paper.md").exists()
    assert (tmp_path / "paper_index.json").exists()
    assert "/session/ses_test_paper/message" in requests


def test_tutor_full_paper_continues_the_opencode_session(tmp_path: Path) -> None:
    class FakePaperAgent:
        def answer(self, **kwargs: object) -> str:
            assert kwargs["session_id"] == "ses_persisted"
            assert "method" in str(kwargs["question"]).lower()
            return "The method has two stages, followed by an ablation study."

    service = PaperTutorService(
        job_id="paper-1",
        run_dir=tmp_path,
        artifacts={
            "parsed_document": {
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": "The method has two stages.",
                        "page": 2,
                        "section": "method",
                    }
                ]
            },
            "opencode_analysis": {
                "session_id": "ses_persisted",
                "provider_id": "opencode-go",
                "model": "qwen3.7-plus",
            },
        },
        paper_agent=FakePaperAgent(),  # type: ignore[arg-type]
    )

    result = service.answer_question(
        {
            "question": "Explain the paper's method in detail.",
            "answer_mode": "full_paper",
        }
    )

    assert result.status == "SUCCESS"
    assert "two stages" in result.answer
    assert result.used_context["opencode_session"] is True
