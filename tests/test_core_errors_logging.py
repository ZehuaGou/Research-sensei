from __future__ import annotations

import logging

from researchsensei.core.errors import MissingDependencyError, SenseiError
from researchsensei.core.logging import redact_secrets, setup_logging


def test_sensei_error_exposes_code_message_and_context_without_secret() -> None:
    error = SenseiError(
        code="CONFIG_MISSING_KEY",
        message="Missing API key. Set MIMO_API_KEY.",
        context={"provider": "mimo"},
    )

    payload = error.to_dict()

    assert payload == {
        "code": "CONFIG_MISSING_KEY",
        "message": "Missing API key. Set MIMO_API_KEY.",
        "context": {"provider": "mimo"},
    }


def test_missing_dependency_error_names_package_and_hint() -> None:
    error = MissingDependencyError("pymupdf", install_hint="pip install pymupdf")

    assert error.code == "MISSING_DEPENDENCY"
    assert "pymupdf" in error.message
    assert error.context["install_hint"] == "pip install pymupdf"


def test_redact_secrets_removes_explicit_secret_and_token_like_values() -> None:
    message = "token sk-live-secret and tp-user-secret should not appear"

    redacted = redact_secrets(message, explicit_secrets=["tp-user-secret"])

    assert "sk-live-secret" not in redacted
    assert "tp-user-secret" not in redacted
    assert "[REDACTED]" in redacted


def test_setup_logging_returns_logger_without_emitting_secret(caplog) -> None:
    logger = setup_logging("researchsensei.test")

    with caplog.at_level(logging.INFO):
        logger.info(redact_secrets("using key sk-live-secret"))

    assert "sk-live-secret" not in caplog.text
    assert "[REDACTED]" in caplog.text
