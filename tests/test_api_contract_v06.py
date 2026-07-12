from __future__ import annotations

from pathlib import Path
from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from researchsensei.core.config import ConfigService
from researchsensei.llm.client import LLMClient
from researchsensei.web.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(workspace_root=tmp_path / "workspace")) as value:
        yield value


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/directions/search", {"query": "graph anomaly detection", "extra": True}),
        ("/api/v1/directions/deep_read", {"candidate": {"title": "x"}, "extra": True}),
        ("/api/v1/directions/seed_expansion", {"seed": {"title": "x"}, "extra": True}),
        ("/api/v1/jobs/missing/ask", {"question": "method?", "extra": True}),
        ("/api/v1/jobs/missing/selection/explain", {"selected_text": "x", "extra": True}),
        ("/api/v1/jobs/missing/formula/explain", {"formula_id": "f1", "extra": True}),
        ("/api/v1/jobs/missing/advisor/question", {"advisor_mode": "group_meeting", "extra": True}),
        ("/api/v1/jobs/missing/advisor/evaluate", {"user_answer": "x", "extra": True}),
        ("/api/v1/settings", {"model": "model", "extra": True}),
    ],
)
def test_request_models_reject_unknown_top_level_fields(
    client: TestClient, path: str, payload: dict[str, object]
) -> None:
    method = client.patch if path == "/api/v1/settings" else client.post

    response = method(path, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_m4_history_and_enum_limits_are_enforced(client: TestClient) -> None:
    history = [{"role": "user", "content": "x"} for _ in range(21)]

    too_many = client.post("/api/v1/jobs/missing/ask", json={"question": "method?", "conversation_history": history})
    bad_role = client.post(
        "/api/v1/jobs/missing/ask",
        json={"question": "method?", "conversation_history": [{"role": "tool", "content": "x"}]},
    )
    bad_mode = client.post(
        "/api/v1/jobs/missing/advisor/question",
        json={"advisor_mode": "anything"},
    )

    assert {too_many.status_code, bad_role.status_code, bad_mode.status_code} == {422}


def test_query_limits_and_long_fields_are_rejected(client: TestClient) -> None:
    responses = [
        client.get("/api/v1/jobs?limit=0"),
        client.get("/api/v1/jobs?limit=201"),
        client.get("/api/v1/library/papers?limit=501"),
        client.post("/api/v1/directions/search", json={"query": "x" * 501}),
        client.post("/api/v1/jobs/missing/ask", json={"question": "x" * 1201}),
    ]

    assert all(response.status_code == 422 for response in responses)
    assert all(response.json()["error"]["code"] == "VALIDATION_ERROR" for response in responses)


def test_deep_read_rejects_semantically_failed_candidate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/directions/deep_read",
        json={
            "candidate": {
                "title": "Clustering Multivariate Time Series",
                "arxiv_id": "2401.00001",
                "relevance_gate_evaluated": True,
                "relevance_gate_passed": False,
                "deep_read_relevance_passed": False,
                "rule_relevance_score": 0.22,
                "relevance_reason": "missing anomaly detection",
            }
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RELEVANCE_GATE_FAILED"
    assert response.json()["detail"]["code"] == "RELEVANCE_GATE_FAILED"


def test_settings_validate_is_explicitly_configuration_only(client: TestClient) -> None:
    response = client.post("/api/v1/settings/validate")

    assert response.status_code == 200
    assert response.json()["validation_mode"] == "configuration_only"
    assert response.json()["live_tested"] is False


def test_live_settings_failure_redacts_secret_and_classifies_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "local.toml"
    config_path.write_text(
        """
active_provider = "deepseek"
[providers.deepseek]
kind = "openai_compatible"
base_url = "https://example.invalid/v1"
api_key_env = "DEEPSEEK_API_KEY"
model = "test"
timeout_seconds = 5
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "super-secret-value")

    async def fail(self: LLMClient, messages, *, config=None):
        raise RuntimeError("connection failed with super-secret-value")

    monkeypatch.setattr(LLMClient, "chat", fail)
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
        )
    )

    response = client.post("/api/v1/settings/validate", json={"live": True, "timeout_seconds": 1})

    assert response.status_code == 200
    assert response.json()["live_tested"] is True
    assert response.json()["error_type"] == "RuntimeError"
    assert "super-secret-value" not in response.text
    assert "[REDACTED]" in response.text
