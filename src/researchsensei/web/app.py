"""Backward-compatible ASGI entry point.

The application factory lives in :mod:`researchsensei.web.app_factory` so the
runtime wiring can be separated from routers and services without changing the
documented ``researchsensei.web.app:create_app`` command.
"""

from researchsensei.web.app_factory import (
    _configured_llm_client,
    _settings_payload,
    create_app,
)

__all__ = ["create_app", "_configured_llm_client", "_settings_payload"]
