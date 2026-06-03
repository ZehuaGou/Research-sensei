from __future__ import annotations

import logging
import re


TOKEN_PATTERN = re.compile(r"\b(?:sk|tp)-[A-Za-z0-9_\-]{6,}\b")


def redact_secrets(message: str, explicit_secrets: list[str] | None = None) -> str:
    redacted = message
    for secret in explicit_secrets or []:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return TOKEN_PATTERN.sub("[REDACTED]", redacted)


def setup_logging(name: str = "researchsensei") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
