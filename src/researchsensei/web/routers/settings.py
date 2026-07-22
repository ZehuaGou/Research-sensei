from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import APIRouter, Request

from researchsensei.core.config import AppConfig, ConfigService, redact_secret
from researchsensei.llm.client import LLMClient, LLMTimeoutError
from researchsensei.llm.ccswitch_bridge import resolve_ccswitch_api_key
from researchsensei.llm.types import ChatMessage, LLMConfig
from researchsensei.web.request_models import SettingsUpdate, SettingsValidationRequest


SettingsPayload = Callable[[AppConfig], dict[str, object]]
EnvWriter = Callable[[str, str, str], None]


def create_settings_router(
    *,
    config_service: ConfigService,
    llm_client: LLMClient | None,
    settings_payload: SettingsPayload,
    env_writer: EnvWriter,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

    @router.get("")
    def get_settings(request: Request) -> dict[str, object]:
        return settings_payload(request.app.state.runtime_config)

    @router.patch("")
    def update_settings(request: Request, payload: SettingsUpdate) -> dict[str, object]:
        model = payload.model
        env_writer(str(config_service.env_path), "RESEARCHSENSEI_LLM_MODEL", model)
        os.environ["RESEARCHSENSEI_LLM_MODEL"] = model
        provider_key = request.app.state.runtime_config.active_provider
        provider = request.app.state.runtime_config.providers[provider_key].model_copy(update={"model": model})
        request.app.state.runtime_config = request.app.state.runtime_config.model_copy(
            update={
                "providers": {
                    **request.app.state.runtime_config.providers,
                    provider_key: provider,
                }
            }
        )
        if llm_client is not None:
            llm_client.provider = llm_client.provider.model_copy(update={"model": model})
        if payload.paper_model:
            paper_model = payload.paper_model
            env_writer(
                str(config_service.env_path),
                "RESEARCHSENSEI_OPENCODE_MODEL",
                paper_model,
            )
            os.environ["RESEARCHSENSEI_OPENCODE_MODEL"] = paper_model
            opencode_config = request.app.state.runtime_config.opencode.model_copy(
                update={"model": paper_model}
            )
            request.app.state.runtime_config = request.app.state.runtime_config.model_copy(
                update={"opencode": opencode_config}
            )
            paper_agent = getattr(request.app.state, "paper_agent", None)
            if paper_agent is not None:
                paper_agent.config = opencode_config
                paper_agent.client.config = opencode_config
        return settings_payload(request.app.state.runtime_config)

    async def validate(request: Request, body: SettingsValidationRequest) -> dict[str, object]:
        public = settings_payload(request.app.state.runtime_config)
        active_provider = str(public.get("active_provider") or "")
        mode = "live_connection" if body.live else "configuration_only"
        if not active_provider:
            return {**public, "ok": False, "message": "No model provider is configured.", "validation_mode": mode, "live_tested": False}
        if not body.live and not public.get("llm_enabled"):
            return {
                **public,
                "ok": False,
                "message": "API LLM is disabled. Set RESEARCHSENSEI_ENABLE_API_LLM=1 to enable live calls.",
                "validation_mode": mode,
                "live_tested": False,
            }
        if not public.get("api_key_configured"):
            return {
                **public,
                "ok": False,
                "message": f"Missing API key. Set environment variable {public.get('api_key_env')}.",
                "validation_mode": mode,
                "live_tested": False,
                "error_type": "MISSING_API_KEY",
            }
        if not body.live:
            return {
                **public,
                "ok": True,
                "message": "Provider configuration is valid. No live LLM call was made.",
                "validation_mode": mode,
                "live_tested": False,
            }

        provider_key = request.app.state.runtime_config.active_provider
        provider = request.app.state.runtime_config.providers[provider_key]
        api_key = resolve_ccswitch_api_key(provider)
        probe = LLMClient(
            provider,
            config=LLMConfig(
                temperature=0.0,
                max_tokens=128,
                json_mode=False,
                timeout=body.timeout_seconds,
                max_retries=0,
                disable_thinking=(
                    provider.kind == "anthropic_compatible"
                    or provider.name == "opencode_go"
                ),
            ),
            api_key_override=api_key,
        )
        try:
            response = await probe.chat([ChatMessage(role="user", content="Reply with OK.")])
        except LLMTimeoutError as error:
            return _live_error(public, provider.api_key_env, "TIMEOUT", "The provider connection timed out.", error)
        except Exception as error:
            return _live_error(public, provider.api_key_env, type(error).__name__, "The provider connection test failed.", error)
        ok = bool(response.content.strip())
        return {
            **public,
            "ok": ok,
            "message": "Provider connection succeeded." if ok else "Provider returned an empty response.",
            "validation_mode": mode,
            "live_tested": True,
            "error_type": "" if ok else "EMPTY_RESPONSE",
        }

    @router.post("/validate")
    async def validate_settings(request: Request, payload: SettingsValidationRequest | None = None) -> dict[str, object]:
        return await validate(request, payload or SettingsValidationRequest())

    @router.post("/test", deprecated=True)
    async def test_settings(request: Request, payload: SettingsValidationRequest | None = None) -> dict[str, object]:
        return await validate(request, payload or SettingsValidationRequest())

    return router


def _live_error(
    public: dict[str, object],
    api_key_env: str,
    error_type: str,
    message: str,
    error: Exception,
) -> dict[str, object]:
    return {
        **public,
        "ok": False,
        "message": message,
        "validation_mode": "live_connection",
        "live_tested": True,
        "error_type": error_type,
        "error_detail": redact_secret(str(error), os.getenv(api_key_env, ""))[:500],
    }
