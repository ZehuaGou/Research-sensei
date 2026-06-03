from __future__ import annotations

from typing import Any


class SenseiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }


class ConfigError(SenseiError):
    pass


class MissingDependencyError(SenseiError):
    def __init__(self, package: str, install_hint: str = "") -> None:
        super().__init__(
            code="MISSING_DEPENDENCY",
            message=f"Missing optional dependency: {package}.",
            context={"package": package, "install_hint": install_hint},
        )
